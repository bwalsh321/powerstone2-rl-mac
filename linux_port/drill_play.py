"""drill_play.py — YOU play the bot's failure moments; your actions become DAgger corrections (Oct 3 2026).

drill_capture.py saved emulator states a few seconds before the bot lost a round. Here you take over the BOT's
seat (in-game P2) from each of those states and play it out. Every decision step records the observation the bot
would have seen (through the env's own observation code, so the old recorder's velocity / last-action bugs cannot
occur) and the action you took, in the bot's 63-action space (direction x button). Your input reaches the game
through the SAME interface the bot uses: one decision every ACTION_FRAMES (~0.1 s); a button you tap at any moment
during a decision window is latched and used at the next decision, the direction is whatever you hold.

Controls (keyboard): arrows = move (two at once = diagonal)  Z = jump(A)  X = action(B)  C = attack(X)
                     V = discard(Y)  A = L (Power Fusion 1)  S = R (Power Fusion 2)
                     P = pause   N = skip this drill (not saved)   ESC / close = quit (progress is kept)
Gamepad: first pygame joystick; hat / d-pad buttons / left stick = move. Xbox-style pads are detected (A jump,
B action, X attack, Y discard, LB/LT = L, RB/RT = R); others use play_vs.py's defaults, --pad-map to remap
(names: jump grab attack throw L R up down left right).

  python drill_play.py --drills drills/leg116 --core "$CORE" --game "../Power Stone 2 (USA).chd"
Writes drills/<tag>/rec_<drill>.npz (obs [T, D], actions [T] in 0..62, rewards, result) and appends to
recordings.jsonl. D = 7 x env.OBS_DIM: 7x160 by default; run with PS2_OBS_V4=1 (Oct 5 2026) to record 7x430 drills
for an obs-v4 bot (dagger.py loads only recordings whose width matches the model and reports the rest). Already-recorded drills are skipped, so you can stop and resume any time.
"""
import argparse, gzip, json, os, time

os.environ.setdefault("PS2_OBS_V2", "1")
os.environ.setdefault("PS2_OBS_V3", "1")
import numpy as np
import pygame

from action_space import BTNS, DIRS, JOINT_N, name as action_name
from play_vs import KEYMAP, PAD_DEFAULT, PAD_TO_RETRO, N_BUTTONS, R_UP, R_DOWN, R_LEFT, R_RIGHT, \
    R_JUMP, R_GRAB, R_ATTACK, R_THROW, R_L, R_R
from sig_guard import keep_native_fault_handlers

DIR_IDX = {n: i for i, (n, _) in enumerate(DIRS)}
BTN_ORDER = [(R_ATTACK, "X"), (R_JUMP, "A"), (R_GRAB, "B"), (R_THROW, "Y"), (R_L, "L"), (R_R, "R")]
BTN_IDX = {n: i for i, (n, *_r) in enumerate(BTNS)}


def mask_to_joint(held, latched):
    """held/latched: RetroPad masks. Direction from what is held now (opposites cancel); button = the first in
    BTN_ORDER that was pressed at any time during the window (latched) or is held now."""
    up, down = held[R_UP] and not held[R_DOWN], held[R_DOWN] and not held[R_UP]
    left, right = held[R_LEFT] and not held[R_RIGHT], held[R_RIGHT] and not held[R_LEFT]
    vert = "up" if up else "down" if down else ""
    horiz = "left" if left else "right" if right else ""
    dname = f"{vert}-{horiz}" if vert and horiz else (vert or horiz or "none")
    b = "none"
    for rid, bname in BTN_ORDER:
        if latched[rid] or held[rid]:
            b = bname
            break
    return DIR_IDX[dname] * len(BTNS) + BTN_IDX[b]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drills", required=True, help="folder written by drill_capture.py")
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", default="../Power Stone 2 (USA).chd")
    ap.add_argument("--max-seconds", type=float, default=20.0, help="end a drill after this long if the round goes on (0 = play the round out)")
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--speed", type=float, default=1.0, help="1.0 = real time")
    ap.add_argument("--instance", type=int, default=12)
    ap.add_argument("--pad-map", default="")
    ap.add_argument("--hidden", action="store_true", help="no window (smoke tests)")
    ap.add_argument("--script", default="", help="smoke test: fixed joint action instead of the keyboard")
    ap.add_argument("--hold", action="store_true", help="old button semantics (held until the next decision); default = taps")
    args = ap.parse_args()

    from obs_stack import FrameStack
    from powerstone_env_libretro import PowerStoneEnvLibretro

    drills = [json.loads(l) for l in open(os.path.join(args.drills, "index.jsonl")) if l.strip()]
    done_log = os.path.join(args.drills, "recordings.jsonl")
    done = {json.loads(l)["drill"] for l in open(done_log)} if os.path.exists(done_log) else set()
    todo = [d for d in drills if d["drill"] not in done]
    print(f"[drill] {len(drills)} drills, {len(done)} already recorded, {len(todo)} to go", flush=True)
    if not todo:
        return

    os.environ["PS2_STAGGER_FRAMES"] = "1"            # no random pre-roll: start exactly at the saved moment
    env = PowerStoneEnvLibretro(core_path=args.core, game_path=args.game, states_dir="./states",
                                state_slots=[todo[0]["slot"]], instance_id=args.instance,
                                bridge_dir=os.path.abspath(f"./bridge_drill_{args.instance}"))
    env.set_action_mode(JOINT_N)
    env.BUTTON_TAP = not args.hold        # Oct 4 2026: buttons are taps, so double jumps and rocket volleys work
    print(f"[drill] buttons: {'held until the next decision (old)' if args.hold else 'taps (double jump / repeated attacks work)'}", flush=True)
    env.MAX_STEPS = 10 ** 9
    K, d = 7, env.OBS_DIM                             # the current bot's input: strided 7-frame stack
    br, emu = env._lr_bridge, env._lr_bridge.emu
    h, w = emu.get_shape()

    if args.hidden and os.uname().sysname == "Linux":
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    # Oct 4 2026: keep reading the controller even when the game window is not focused (macOS drops joystick
    # events for background windows otherwise).
    os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
    with keep_native_fault_handlers():
        pygame.init()
    pygame.joystick.init()
    pad = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
    if pad:
        pad.init()
    padmap = dict(PAD_DEFAULT)
    # Oct 4 2026 (Blake's Xbox Series X on the M4): SDL reports these pads with the d-pad as BUTTONS 11-14
    # (up, down, left, right), bumpers 9/10 and analog triggers on axes 4/5. Face buttons line up with the
    # Dreamcast's positions: A = jump, B = action, X = attack, Y = discard.
    xbox_like = bool(pad) and any(k in pad.get_name().lower() for k in ("xbox", "xinput"))
    if xbox_like:
        padmap.update(jump=0, grab=1, attack=2, throw=3, L=9, R=10, up=11, down=12, left=13, right=14)
    for kv in filter(None, args.pad_map.split(",")):
        k, v = kv.split("="); padmap[k.strip()] = int(v)
    if pad:
        print(f"[drill] controller: {pad.get_name()} ({pad.get_numbuttons()} buttons, {pad.get_numhats()} hats, "
              f"{pad.get_numaxes()} axes) map={padmap}" + (" + triggers on axes 4/5" if xbox_like else ""), flush=True)
    DPAD = {"up": R_UP, "down": R_DOWN, "left": R_LEFT, "right": R_RIGHT}
    screen = pygame.display.set_mode((w * args.scale, h * args.scale), pygame.HIDDEN if args.hidden else 0)
    clock = pygame.time.Clock()
    buf = np.zeros((h, w, 3), np.uint8)
    st = {"quit": False, "skip": False, "paused": False}
    latched = np.zeros(N_BUTTONS, np.uint8)

    def human_mask():
        m = np.zeros(N_BUTTONS, np.uint8)
        keys = pygame.key.get_pressed()
        for k, rid in KEYMAP.items():
            if keys[k]:
                m[rid] = 1
        if pad is not None:
            if pad.get_numhats() > 0:
                hx, hy = pad.get_hat(0)
                m[R_RIGHT] |= hx > 0; m[R_LEFT] |= hx < 0; m[R_UP] |= hy > 0; m[R_DOWN] |= hy < 0
            if pad.get_numaxes() >= 2:
                ax, ay = pad.get_axis(0), pad.get_axis(1)
                m[R_RIGHT] |= ax > 0.5; m[R_LEFT] |= ax < -0.5; m[R_DOWN] |= ay > 0.5; m[R_UP] |= ay < -0.5
            for nm, bid in padmap.items():
                if bid >= pad.get_numbuttons() or not pad.get_button(bid):
                    continue
                if nm in PAD_TO_RETRO:
                    m[PAD_TO_RETRO[nm]] = 1
                elif nm in DPAD:                          # d-pad reported as buttons
                    m[DPAD[nm]] = 1
            if xbox_like and pad.get_numaxes() >= 6:      # analog triggers: LT -> L, RT -> R
                m[R_L] |= pad.get_axis(4) > 0.5; m[R_R] |= pad.get_axis(5) > 0.5
        return m

    def pump():
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                st["quit"] = True
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: st["quit"] = True
                elif ev.key == pygame.K_p: st["paused"] = not st["paused"]
                elif ev.key == pygame.K_n: st["skip"] = True

    orig_run = br.run_frames

    def run_frames_paced(n):                          # render + pace every frame; latch button presses
        for _ in range(n):
            pump()
            while st["paused"] and not st["quit"]:
                pump(); clock.tick(30)
            if st["quit"] or st["skip"]:
                raise KeyboardInterrupt
            latched[:] |= human_mask()
            orig_run(1)
            emu.get_frame(buf, w, h)
            surf = pygame.surfarray.make_surface(np.transpose(buf[::-1], (1, 0, 2)))
            if args.scale != 1:
                surf = pygame.transform.scale(surf, (w * args.scale, h * args.scale))
            screen.blit(surf, (0, 0)); pygame.display.flip()
            if args.speed > 0:
                clock.tick(60 * args.speed)

    out = open(done_log, "a")
    for i, dm in enumerate(todo):
        blob = gzip.open(os.path.join(args.drills, dm["drill"] + ".state.gz"), "rb").read()

        def load_drill(_slot, _blob=blob):            # env.reset() loads the drill instead of the lineup state
            if br.emu.set_state(_blob) is False:
                raise RuntimeError(f"core rejected {dm['drill']}")
            br.clear_inputs()
            for s in br._synths:
                s.on_loadstate()
            orig_run(2)
        br.loadstate = load_drill
        env.STATE_SLOTS = [dm["slot"]]
        pygame.display.set_caption(f"DRILL {i + 1}/{len(todo)}  {dm['drill']}  slot{dm['slot']}  "
                                   f"KO was {dm['seconds_before_ko']}s away  — you are P2 (the bot)  N=skip ESC=quit")
        br.run_frames = orig_run
        # Oct 4 2026: env.reset() waits for a "match ready" state, which requires the bot above 100/1000 health.
        # Many drills are the bot's last seconds at LOW health (exactly the moments worth correcting), so the
        # reset reloaded them forever (drill_004 froze the Mac). While loading a drill: alive is enough.
        _ai = env.AGENT_PLAYER - 1
        env._match_ready = lambda s, provisional=False: s["h"][_ai] > 0 and any(
            h > 0 for j, h in enumerate(s["h"]) if j != _ai)
        try:
            o = np.asarray(env.reset(), np.float32)[:d]
        finally:
            del env._match_ready                          # back to the class's check for the round itself
        fs = FrameStack(K, d); obs = fs.reset(o)
        br.run_frames = run_frames_paced
        rec_obs, rec_act, rec_rew = [], [], []
        latched[:] = 0
        result, t0 = "cut", time.time()
        try:
            for _step in range(int(args.max_seconds / 0.1) if args.max_seconds > 0 else 10 ** 6):
                a = int(args.script) if args.script else mask_to_joint(human_mask(), latched)
                latched[:] = 0
                rec_obs.append(obs.copy()); rec_act.append(a)
                o2, r, dn, info = env.step(a)
                rec_rew.append(float(r))
                obs = fs.push(np.asarray(o2, np.float32)[:d])
                if dn:
                    result = info.get("result", "timeout")
                    break
        except KeyboardInterrupt:
            if st["quit"]:
                break
            st["skip"] = False
            print(f"[drill] {dm['drill']} skipped", flush=True)
            continue
        finally:
            br.run_frames = orig_run
        np.savez_compressed(os.path.join(args.drills, f"rec_{dm['drill']}.npz"), obs=np.asarray(rec_obs, np.float32),
                            actions=np.asarray(rec_act, np.int64), rewards=np.asarray(rec_rew, np.float32),
                            result=result, button_tap=np.bool_(env.BUTTON_TAP))
        rec = dict(drill=dm["drill"], steps=len(rec_act), result=result, seconds=round(time.time() - t0, 1),
                   button_tap=bool(env.BUTTON_TAP),
                   combos=int(sum(1 for x in rec_act if x not in (7, 14, 21, 28, 1, 2, 3, 4, 5, 6))),
                   top=action_name(max(set(rec_act), key=rec_act.count)) if rec_act else "")
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(f"[drill] {dm['drill']}: {result} after {len(rec_act)} decisions ({rec['combos']} combos)", flush=True)
    print("[drill] session over", flush=True)
    # Oct 4 2026: every recording is already on disk; skip interpreter teardown, where the core's threads abort on
    # macOS ("mutex lock failed").
    os._exit(0)


if __name__ == "__main__":
    main()
