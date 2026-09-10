"""PowerStoneEnvV6 on libretro — same obs, same rewards, same model; no files.

Subclasses the existing env and overrides ONLY the transport layer:
  * _send()            -> executes the command against FlycastBridge
                          synchronously (frames actually run inside it)
  * _parse_state_once() -> parses the in-memory line from StateLineSynth
                          using the parent parser unchanged (we hand it a
                          StringIO through _state_file indirection-free path:
                          we simply override the read, not the parse)

Everything else — obs bus, reward terms, episode accounting, ep_stats CSV,
curriculum slots — runs the parent code verbatim, so the Windows-trained
checkpoints load and behave identically once parity is verified.

Requires: powerstone_env_v6.py, ps2_addr.py, ps2_ram.py, flycast_bridge.py
on PYTHONPATH, and per-slot savestates recreated under the libretro core
(states_dir/slot<N>.state — see docs/README_PORT.md; standalone .state files do
NOT load in the libretro core).
"""
import io
import os
import random

from powerstone_env_v6 import PowerStoneEnvV6
from ps2_ram import StateLineSynth
from flycast_bridge import FlycastBridge


class PowerStoneEnvLibretro(PowerStoneEnvV6):
    def __init__(self, core_path, game_path, states_dir,
                 bridge_dir=None, instance_id=0, state_slots=None,
                 bot_port=1):
        """bot_port: libretro player index the bot's pad maps to.
        DC port B (in-game P2, the Windows convention) = index 1."""
        self._lr_bridge = FlycastBridge(core_path, game_path, states_dir,
                                        instance_id)
        self._lr_synth = StateLineSynth(self._lr_bridge.ram, bot_player=2)
        self._lr_bridge.attach_synth(self._lr_synth)
        self._lr_bot_port = bot_port
        # PS2_FRAME_SLIP: extra frames run after every press/axis command,
        # input held — emulates the lua-era rig, where the emulator kept
        # free-running while python computed the next action. 0 = exact
        # commanded cadence (default). Diagnostic knob for the gate-4
        # parity miss: try 2-4 to mimic rig latency at turbo speed.
        self._lr_slip = int(os.environ.get("PS2_FRAME_SLIP", "0"))
        # Prime the synth: the parent __init__ sanity-reads a state line
        # before any command has run frames (in the lua era a background
        # process produced lines continuously). A few ticks materialize one.
        self._lr_bridge.run_frames(4)
        # bridge_dir still used for ep_stats_v6.csv output; default per-instance
        bridge_dir = bridge_dir or os.path.abspath(f"./bridge_i{instance_id}")
        os.makedirs(bridge_dir, exist_ok=True)
        # turbo MUST be False: no pydirectinput on Linux, and speed comes from
        # uncapped core.run() instead of F9.
        super().__init__(bridge_dir=bridge_dir, turbo=False,
                         state_slots=state_slots)

    # ---------------------------------------------------------- transport
    def _send(self, cmd):
        self._seq = self._lr_bridge.execute(cmd)
        if self._lr_slip and cmd.startswith(("press", "axis")):
            self._lr_bridge.run_frames(self._lr_slip)
        if cmd.startswith("loadstate"):
            # Aug 24 fix #3 (the "still trying to restart the match" loop):
            # Windows savestates were stamped MID-FIGHT, so in the lua era
            # loadstate instantly showed live healths. Our libretro states
            # are stamped at round start and need the intro to play out
            # (~306 frames for slot2, measured with diag_state.py). The
            # parent's match-ready loop can't get there: its wall-clock
            # poll budget pumps too few frames per try and every 3rd try
            # RELOADS the state, wiping progress. Restore the old
            # invariant instead: pump the intro out right here, so the
            # parent's first read after any loadstate sees a live match.
            for _ in range(40):                 # 40 x 30 = 1200-frame cap
                s = self._parse_state_once()
                if s is not None and self._match_ready(s, provisional=True):
                    break
                self._lr_bridge.run_frames(30)
            # Aug 24 fix #4: with a deterministic policy the frame-locked
            # loadstate above replays BYTE-IDENTICAL episodes (seen live in
            # eval_parity: eps 2-5 with identical stats). The Windows rig
            # got per-episode frame-alignment jitter for free from its
            # background emulator; re-create that spread with a random
            # 0-59 frame stagger. In-distribution, harmless for training.
            # 0-599 (was 0-59: birthday collisions left ~35-40 distinct
            # episodes out of 50 — pairs 2/10, 16/25, 23/50, 40/47 observed
            # bit-identical in the Aug 24 parity run).
            self._lr_bridge.run_frames(random.randrange(600))

    def _parse_state_once(self):
        line = self._lr_synth.line
        if not line:
            return None
        # Aug 24 fix #2 (the eval_parity hang): lua-era code "waits" in
        # wall-clock poll loops — reset()'s match-ready loop, _wait_frames —
        # assuming a BACKGROUND emulator advances the game underneath.
        # Here nothing advances unless we pump, so a re-read of the same
        # synth frame would spin forever (loadstate -> poll unchanged state
        # -> loadstate ...). If the same frame is about to be parsed twice,
        # run one frame first: "waiting" then makes progress exactly like
        # the lua era, at poll speed. Fresh post-action reads (frames just
        # ran inside execute()) are untouched, so step cadence is identical.
        if getattr(self, "_last_parsed_frame", None) == self._lr_synth.frame:
            self._lr_bridge.run_frames(1)
            line = self._lr_synth.line
        self._last_parsed_frame = self._lr_synth.frame
        # Parent parser reads from a file path; feed it the in-memory line
        # through a tiny shim: temporarily point _state_file at a StringIO
        # via os-level indirection is not possible, so we replicate the two
        # lines of I/O and call the parent's pure parsing by monkey-shim:
        return self._parse_line(line)

    def _parse_line(self, line):
        """Identical to the parent's _parse_state_once minus the file read.
        Implemented by delegating through a temp in-memory file."""
        import tempfile
        # cheap and safe: parse via the parent using a real tmpfs-backed file
        # once per call would defeat the point — instead we exploit that the
        # parent method only does open(self._state_file).read(); give it a
        # /dev/shm file that we rewrite in place.
        if not hasattr(self, "_shm_path"):
            # /dev/shm on Linux; macOS has no shm mount — default tmp dir
            # (on APFS with an M-series this is effectively RAM-cached anyway)
            shm = "/dev/shm" if os.path.isdir("/dev/shm") else None
            fd, self._shm_path = tempfile.mkstemp(
                prefix="ps2_state_", dir=shm)
            os.close(fd)
            self._state_file = self._shm_path
        with open(self._shm_path, "w") as f:
            f.write(line)
        return super()._parse_state_once()

    # ----------------------------------------------------------- liveness
    def _wait_for_bridge(self):
        """Aug 24 fix (the gate-4 smoke blocker): the parent's liveness
        check assumes a BACKGROUND emulator whose frame counter advances in
        wall time (lua era: Flycast ran free, the lua wrote a line every
        vblank). Here frames advance ONLY when we pump them — the synth's
        `frame` is its own tick counter, incremented once per run_frames()
        iteration — so the parent's time.sleep(0.3) between two reads
        always sees the same frame and raises "Bridge frame counter not
        advancing" on every attempt. Same check, but pump frames between
        the two reads. (This, not the state-file path, was the smoke
        failure: _read_state does go through our _parse_state_once.)"""
        s1 = self._read_state()
        self._lr_bridge.run_frames(4)
        s2 = self._read_state()
        if s1["frame"] == s2["frame"]:
            raise RuntimeError(
                "frame counter not advancing across run_frames(4) — core "
                "not stepping, or synth not attached to the bridge?")
        print(f"[env] bridge alive (frame {s2['frame']}, "
              f"line={'v7' if s2.get('v7') else ('v6' if s2.get('v6') else ('v5' if s2.get('v5') else ('v4' if s2['v4'] else 'v3 FALLBACK')))}"
              f" obs_dim={self.OBS_DIM} actions={len(self.ACTIONS)})")
        if s2.get("v6") and not s2.get("v7"):
            print("[env] WARNING: v6 line but not v7 — chest obs will read "
                  "zero. Check StateLineSynth._compose field count.")
        if not s2.get("v6"):
            print("[env] WARNING: not receiving the v6/v7 line. Stone y, "
                  "form meters, items and projectiles will all read 0.0. "
                  "Check StateLineSynth against _parse_state_once.")

    # ------------------------------------------------------------- misc
    def close(self):
        try:
            self._lr_bridge.close()
        finally:
            if hasattr(self, "_shm_path"):
                try:
                    os.unlink(self._shm_path)
                except OSError:
                    pass


if __name__ == "__main__":
    # smoke test: boot, load slot 1, take 100 random steps
    import numpy as np
    env = PowerStoneEnvLibretro(
        core_path=os.environ.get("PS2_CORE", "../cores/flycast_libretro.so"),
        game_path=os.environ.get("PS2_GAME", "../Power Stone 2 (USA).chd"),
        states_dir=os.environ.get("PS2_STATES", "./states"),
        state_slots=[1],
    )
    obs = env.reset()
    total = 0.0
    for i in range(100):
        obs, r, done, info = env.step(env.action_space.sample())
        total += r
        if done:
            obs = env.reset()
    print(f"smoke OK — 100 steps, cumulative reward {total:+.2f}")
    env.close()
