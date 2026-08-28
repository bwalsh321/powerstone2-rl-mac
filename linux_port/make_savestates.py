"""Interactive savestate creator for the libretro core.

Standalone-Flycast .state files do NOT load in flycast-libretro, so the
curriculum savestates must be recreated once under the new core. This tool
gives you a window (works over X11 forwarding / VNC to the headless box, or
run it on any Linux desktop and copy the states over) with keyboard
controls to navigate menus, set up the match, and stamp savestates.

Keys:
  arrows = dpad     z = DC A    x = DC B    a = DC X    s = DC Y
  enter  = Start    q = L trig  w = R trig
  TAB    = switch which DC port the keyboard drives (for 2P VS setup!)
  F1..F7 = save slot1..slot7.state         ESC = quit

A gamepad (Xbox etc.), if connected, drives the SAME port the keyboard
does (TAB switches both). Unmapped buttons print their raw index so the
JOY_BUTTONS table below can be corrected in seconds.

For self-play savestates: set up a VS match with BOTH ports as human
players (TAB to port A, join, TAB to port B, join), pick characters/stage,
save the state at round start. For CPU-opponent states, mirror the Windows
lineup (P2 human, COM level set in the game's options menu first).
"""
import argparse
import gzip
import os

import numpy as np
import pygame

import _retro

KEYMAP = {  # pygame key -> RetroPad id
    pygame.K_UP: 4, pygame.K_DOWN: 5, pygame.K_LEFT: 6, pygame.K_RIGHT: 7,
    pygame.K_z: 0, pygame.K_x: 8, pygame.K_a: 1, pygame.K_s: 9,
    pygame.K_RETURN: 3, pygame.K_q: 12, pygame.K_w: 13,
}

# gamepad raw button index -> RetroPad id, SDL controller ordering (verified
# on Xbox Series X pad / macOS: A0 B1 X2 Y3 back4 guide5 start6 Ls7 Rs8
# LB9 RB10 dpadU11 dpadD12 dpadL13 dpadR14 share15).
# A=DC A(0), B=DC B(8), X=DC X(1), Y=DC Y(9), start -> Start(3).
JOY_BUTTONS = {0: 0, 1: 8, 2: 1, 3: 9, 6: 3}
JOY_TRIG_AXES = {4: 12, 5: 13}     # LT/RT analog axes -> L2/R2 (threshold)
JOY_DPAD_BUTTONS = {11: 4, 12: 5, 13: 6, 14: 7}   # dpad arrives as buttons


def read_joystick(joy, mask):
    """OR a connected pad's state into a 16-slot retro mask."""
    # dpad: hat if present, else left stick
    if joy.get_numhats() > 0:
        hx, hy = joy.get_hat(0)
        if hy > 0: mask[4] = 1
        if hy < 0: mask[5] = 1
        if hx < 0: mask[6] = 1
        if hx > 0: mask[7] = 1
    ax = joy.get_axis(0) if joy.get_numaxes() > 0 else 0.0
    ay = joy.get_axis(1) if joy.get_numaxes() > 1 else 0.0
    if ay < -0.5: mask[4] = 1
    if ay > 0.5:  mask[5] = 1
    if ax < -0.5: mask[6] = 1
    if ax > 0.5:  mask[7] = 1
    for b, rid in JOY_BUTTONS.items():
        if b < joy.get_numbuttons() and joy.get_button(b):
            mask[rid] = 1
    for b, rid in JOY_DPAD_BUTTONS.items():
        if b < joy.get_numbuttons() and joy.get_button(b):
            mask[rid] = 1
    for a, rid in JOY_TRIG_AXES.items():
        if a < joy.get_numaxes() and joy.get_axis(a) > 0.0:
            mask[rid] = 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--states", default="./states")
    ap.add_argument("--scale", type=int, default=2)
    args = ap.parse_args()
    os.makedirs(args.states, exist_ok=True)

    emu = _retro.RetroEmulator()
    # HLE BIOS (no real BIOS files in this project) + VMUs in port A/B slot 1.
    # flycast attaches expansion devices only on a post-startup variables
    # update; set_variable raises that flag so the first run() applies them.
    emu.set_variable("flycast_hle_bios", "enabled")
    emu.set_variable("reicast_hle_bios", "enabled")
    emu.set_variable("flycast_device_port1_slot1", "VMU")
    emu.set_variable("flycast_device_port2_slot1", "VMU")
    emu.set_variable("flycast_threaded_rendering", "disabled")
    emu.set_variable("reicast_threaded_rendering", "disabled")
    emu.init(args.core.encode(), args.game.encode(), 0)
    for _ in range(60):
        emu.run()
    h, w = emu.get_shape()
    pygame.init()
    pygame.joystick.init()
    joy = None
    if pygame.joystick.get_count() > 0:
        joy = pygame.joystick.Joystick(0)
        joy.init()
        print(f"gamepad: {joy.get_name()} "
              f"({joy.get_numbuttons()} buttons, {joy.get_numaxes()} axes, "
              f"{joy.get_numhats()} hats) — drives the active port")
    screen = pygame.display.set_mode((w * args.scale, h * args.scale))
    pygame.display.set_caption("PS2 savestate maker — TAB switches port")
    clock = pygame.time.Clock()
    buf = np.zeros((h, w, 3), np.uint8)

    port = 0
    masks = {0: np.zeros(16, np.uint8), 1: np.zeros(16, np.uint8)}
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_TAB:
                    port = 1 - port
                    print(f"keyboard now drives DC port {'AB'[port]}")
                elif pygame.K_F1 <= ev.key <= pygame.K_F7:
                    slot = ev.key - pygame.K_F1 + 1
                    p = os.path.join(args.states, f"slot{slot}.state")
                    with gzip.open(p, "wb") as fh:
                        fh.write(emu.get_state())
                    print(f"saved {p}")
                elif ev.key in KEYMAP:
                    masks[port][KEYMAP[ev.key]] = 1
            elif ev.type == pygame.KEYUP and ev.key in KEYMAP:
                masks[port][KEYMAP[ev.key]] = 0
            elif ev.type == pygame.JOYBUTTONDOWN and ev.button not in JOY_BUTTONS:
                print(f"unmapped joy button: {ev.button} "
                      f"(add to JOY_BUTTONS if it should do something)")

        for p in (0, 1):
            m = masks[p].copy()
            if joy is not None and p == port:
                read_joystick(joy, m)
            emu.set_button_mask(m, p)
        emu.run()
        emu.get_frame(buf, w, h)
        # GL reads frames bottom-up -> flip vertically for display
        surf = pygame.surfarray.make_surface(np.transpose(buf[::-1], (1, 0, 2)))
        if args.scale != 1:
            surf = pygame.transform.scale(surf, (w * args.scale, h * args.scale))
        screen.blit(surf, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    emu.close()   # join core threads before interpreter teardown


if __name__ == "__main__":
    main()
