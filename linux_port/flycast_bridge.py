"""In-process replacement for the lua/file bridge, on sdlarch-rl's RetroEmulator.

Replicates the lua command channel's semantics exactly:
  * press <dc_mask> <frames>  — set buttons, run <frames> frames, then KEEP
    the mask held (Aug-16 HOLD-UNTIL-NEXT: a bare press persists until the
    next press/axis replaces it; loadstate clears all held input).
  * axis <id> <val> <frames>  — DC L/R triggers (standalone ids 5/6) become
    RetroPad L2/R2 digital full-press (sdlarch returns 32767 for analog
    buttons in the mask).
  * loadstate <n>             — retro_unserialize from states_dir/slot<n>.state
    (gzip'd bytes, sdlarch-rl .state convention), clears held input.

DC bitmask -> RetroPad id mapping (flycast libretro conventions; verify once
with calibrate_buttons.py — if a button is swapped, fix DC_TO_RETRO here and
nothing else):
    DC A (0x004) -> RetroPad B (0)      DC B (0x002) -> RetroPad A (8)
    DC X (0x400) -> RetroPad Y (1)      DC Y (0x200) -> RetroPad X (9)
    Start(0x008) -> START (3)           dpad U/D/L/R -> 4/5/6/7
    L trig (axis 5) -> L2 (12)          R trig (axis 6) -> R2 (13)
"""
import gzip
import os

import numpy as np

import _retro   # built by sdlarch-rl (cmake); or `from sdlarch_rl import ...`

N_BUTTONS = 16
DC_TO_RETRO = {
    0x002: 8,    # DC B  -> RetroPad A
    0x004: 0,    # DC A  -> RetroPad B
    0x008: 3,    # Start -> START
    0x010: 4,    # Up
    0x020: 5,    # Down
    0x040: 6,    # Left
    0x080: 7,    # Right
    0x200: 9,    # DC Y  -> RetroPad X
    0x400: 1,    # DC X  -> RetroPad Y
}
AXIS_TO_RETRO = {5: 12, 6: 13}   # standalone-lua axis ids -> L2 / R2


class FlycastBridge:
    def __init__(self, core_path, game_path, states_dir, instance_id=0):
        self.emu = _retro.RetroEmulator()
        # README_MIGRATION correction: no real BIOS files exist in this project;
        # flycast's built-in HLE BIOS is what the Windows rig always ran on.
        # (modern core uses the flycast_ prefix; reicast_ kept for older builds)
        self.emu.set_variable("flycast_hle_bios", "enabled")
        self.emu.set_variable("reicast_hle_bios", "enabled")
        # VMUs in port A/B slot 1 (flycast attaches expansion devices only on a
        # post-startup variables update; these raise the update flag).
        self.emu.set_variable("flycast_device_port1_slot1", "VMU")
        self.emu.set_variable("flycast_device_port2_slot1", "VMU")
        # Threaded rendering races our frontend at init/teardown; single-thread
        # is also the deterministic mode the RL loop wants.
        self.emu.set_variable("flycast_threaded_rendering", "disabled")
        self.emu.set_variable("reicast_threaded_rendering", "disabled")
        self.emu.init(core_path.encode(), game_path.encode(), instance_id)
        self.states_dir = states_dir
        self.ram = self.emu.get_ram()           # zero-copy SYSTEM_RAM view
        self._held = {}                          # player -> np.uint8[16]
        self._default_player = 1                 # libretro port the bot drives
                                                 # (DC port B / in-game P2)
        self._synths = []                        # StateLineSynth per agent
        self._seq = 0

    # ------------------------------------------------------------- agents
    def attach_synth(self, synth):
        self._synths.append(synth)

    # -------------------------------------------------------------- frames
    def run_frames(self, n):
        for _ in range(n):
            self.emu.run()
            for s in self._synths:
                s.tick(self._seq)

    # ------------------------------------------------------------- inputs
    def _mask_for(self, player):
        if player not in self._held:
            self._held[player] = np.zeros(N_BUTTONS, np.uint8)
        return self._held[player]

    def press(self, dc_mask, frames, player=None):
        player = self._default_player if player is None else player
        m = np.zeros(N_BUTTONS, np.uint8)
        for bit, rid in DC_TO_RETRO.items():
            if dc_mask & bit:
                m[rid] = 1
        self._held[player] = m
        self.emu.set_button_mask(m, player)
        self.run_frames(frames)
        # hold-until-next: mask stays set after the frames elapse.

    def axis(self, axis_id, value, frames, player=None):
        player = self._default_player if player is None else player
        m = np.zeros(N_BUTTONS, np.uint8)
        rid = AXIS_TO_RETRO.get(axis_id)
        if rid is not None and abs(value) > 0.01:
            m[rid] = 1
        self._held[player] = m
        self.emu.set_button_mask(m, player)
        self.run_frames(frames)

    def clear_inputs(self):
        z = np.zeros(N_BUTTONS, np.uint8)
        for p in list(self._held) or [0, 1]:
            self.emu.set_button_mask(z, p)
        self._held.clear()

    # ---------------------------------------------------------- savestates
    def loadstate(self, slot):
        path = os.path.join(self.states_dir, f"slot{slot}.state")
        with gzip.open(path, "rb") as fh:
            self.emu.set_state(fh.read())
        self.clear_inputs()                      # lua parity: menus never see
        for s in self._synths:                   # a stuck button
            s.on_loadstate()
        self.run_frames(2)                       # let the core settle a frame

    def savestate(self, slot):
        path = os.path.join(self.states_dir, f"slot{slot}.state")
        os.makedirs(self.states_dir, exist_ok=True)
        with gzip.open(path, "wb") as fh:
            fh.write(self.emu.get_state())

    # ------------------------------------------------------------ commands
    def execute(self, cmd):
        """Execute one lua-channel command string. Returns the ack seq."""
        self._seq += 1
        parts = cmd.split()
        if parts[0] == "press":
            self.press(int(parts[1]), int(parts[2]))
        elif parts[0] == "axis":
            self.axis(int(parts[1]), float(parts[2]), int(parts[3]))
        elif parts[0] == "loadstate":
            self.loadstate(int(parts[1]))
        elif parts[0] == "player":
            # lua parity: declares which IN-GAME player the bot drives.
            # in-game N (1-based) -> libretro port N-1 ("player 2" = port 1).
            self._default_player = int(parts[1]) - 1
        else:
            raise ValueError(f"unknown bridge command: {cmd!r}")
        return self._seq

    def close(self):
        self.emu.close()
