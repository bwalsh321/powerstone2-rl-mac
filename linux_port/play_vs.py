"""play_vs.py — YOU (P1, keyboard or gamepad) against the trained bot, live.

Sep 16 2026. Built so Blake can measure the thing the lv8 number cannot:
does the bot beat a human? The bot sits in in-game P2 exactly as in
training/eval; you drive in-game P1 (libretro port 0) frame by frame.

Modes (--mode):
  1v1    states/slot1.state (2-seat self-play state): you vs the bot.
  ffa    states/slot0.state (4 HUMAN): you vs the bot + two more policy
         seats (P3, P4) — "me against three of my own bots".
  mixed  states_mixed/slot0.state: you vs the bot + a policy in P3 + the
         game's lv3 COM in P4 (the leg 34+ training arena).
--opps same (default) puts the SAME model in every policy seat; --opps pool
samples them from pool_league like training does.

Keyboard (P1):  arrows = move   Z = jump(A)  X = grab(B)  C = attack(X)
                V = throw(Y)    A = L (PF1)  S = R (PF2)   Enter = Start
                P = pause   ESC / close window = quit
Gamepad: first pygame joystick if present. Hat/left stick = move; buttons
0/1/2/3 = jump/grab/attack/throw, 4/5 = L/R, 7 = Start (--show-pad prints
button ids so you can remap with --pad-map "jump=0,grab=1,attack=2,throw=3,L=4,R=5,start=7").

The episode never times out (MAX_STEPS lifted); a round ends when the game
ends it. Results print from the BOT's side (win/loss); in 3+ player modes a
bot loss is not automatically your win — the screen tells you that.

Usage (linux_port/, venv active, the p4 harness on PYTHONPATH):
  SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PS2_OBS_V2=1 \
    python -u play_vs.py --core "$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" \
    --game "../Power Stone 2 (USA).chd" --mode 1v1 --model ./powerstone_v6_leg38_league.zip
Use an --instance no trainer/battery is using (default 12).
"""
import argparse
import os

os.environ.setdefault("PS2_OBS_V2", "1")
os.environ.setdefault("PS2_FFA_MAX_STEPS", "1000000000")

import numpy as np
import pygame
from sig_guard import keep_native_fault_handlers
from stable_baselines3 import PPO

from powerstone_env_libretro import PowerStoneEnvLibretro

# RetroPad ids (flycast_bridge.DC_TO_RETRO / AXIS_TO_RETRO)
R_JUMP, R_GRAB, R_ATTACK, R_THROW = 0, 8, 1, 9      # DC A, B, X, Y
R_UP, R_DOWN, R_LEFT, R_RIGHT, R_START = 4, 5, 6, 7, 3
R_L, R_R = 12, 13
N_BUTTONS = 16

KEYMAP = {
    pygame.K_UP: R_UP, pygame.K_DOWN: R_DOWN, pygame.K_LEFT: R_LEFT, pygame.K_RIGHT: R_RIGHT,
    pygame.K_z: R_JUMP, pygame.K_x: R_GRAB, pygame.K_c: R_ATTACK, pygame.K_v: R_THROW,
    pygame.K_a: R_L, pygame.K_s: R_R, pygame.K_RETURN: R_START,
}
PAD_DEFAULT = {"jump": 0, "grab": 1, "attack": 2, "throw": 3, "L": 4, "R": 5, "start": 7}
PAD_TO_RETRO = {"jump": R_JUMP, "grab": R_GRAB, "attack": R_ATTACK, "throw": R_THROW,
                "L": R_L, "R": R_R, "start": R_START}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--model", default="./powerstone_v6_leg38_league.zip")
    ap.add_argument("--mode", choices=["1v1", "ffa", "mixed"], default="1v1")
    ap.add_argument("--opps", choices=["same", "pool"], default="same")
    ap.add_argument("--stochastic", action="store_true", help="bot samples actions (eval uses deterministic)")
    ap.add_argument("--episodes", type=int, default=0, help="0 = until quit")
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--speed", type=float, default=1.0, help="1.0 = real time; 0 = uncapped (smoke)")
    ap.add_argument("--instance", type=int, default=12)
    ap.add_argument("--hidden", action="store_true")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--show-pad", action="store_true")
    ap.add_argument("--pad-map", default="")
    ap.add_argument("--max-steps", type=int, default=0, help="smoke only: cap env steps per episode")
    args = ap.parse_args()

    bridge_dir = os.path.abspath(f"./bridge_play_{args.instance}")
    from recurrent_policy import load_model, PolicyRunner   # Oct 2: PPO or RecurrentPPO
    model = load_model(args.model)
    runner = PolicyRunner(model)
    from obs_stack import k_for, FrameStack            # Sep 22: stacked policies
    from obs_stack import kd_for
    _k, _d = kd_for(model); _fs = FrameStack(_k, _d) if _k > 1 else None   # Sep 23: v3 models are 160/frame
    _sl = (lambda o: o[:_d])                                   # a v2 model under an obs v3 env reads obs[:122]
    if args.mode == "1v1":
        env = PowerStoneEnvLibretro(core_path=args.core, game_path=args.game, states_dir="./states",
                                    state_slots=[1], instance_id=args.instance, bridge_dir=bridge_dir)
        env._legacy_proj_main = env._legacy_proj = (_d == 122)      # Sep 28 (Astra 3): main-model contract
        env._legacy_item_main = env._legacy_item = (_d <= 160)     # Oct 5 (obs v4): main-model contract
        assert _d <= env.OBS_DIM, f"model reads {_d}/frame but the env builds {env.OBS_DIM}: set PS2_OBS_V4=1"
    else:
        from ffa_selfplay_env import FFASelfPlayEnv
        states_dir = "./states" if args.mode == "ffa" else "./states_mixed"
        seats = (2, 3) if args.mode == "ffa" else (2,)
        env = FFASelfPlayEnv(core_path=args.core, game_path=args.game, states_dir=states_dir,
                             state_slots=[0], instance_id=args.instance, bridge_dir=bridge_dir,
                             pool_dir="./pool_league", seats=seats, sampling="uniform",
                             opp_deterministic=not args.stochastic)
        env._legacy_proj_main = env._legacy_proj = (_d == 122)      # Sep 28 (Astra 3): main-model contract
        env._legacy_item_main = env._legacy_item = (_d <= 160)     # Oct 5 (obs v4): main-model contract
        assert _d <= env.OBS_DIM, f"model reads {_d}/frame but the env builds {env.OBS_DIM}: set PS2_OBS_V4=1"
        if args.opps == "same":
            def _same():
                env._pool.last_path = args.model
                return model
            env._pool.sample = _same
    env.set_action_mode(int(model.action_space.n))   # Oct 3 2026: 10 legacy / 63 joint (action_space.py)
    env.MAX_STEPS = args.max_steps if args.max_steps > 0 else 10 ** 9

    br = env._lr_bridge
    emu = br.emu
    h, w = emu.get_shape()
    with keep_native_fault_handlers():   # Oct 1: pygame's parachute kills flycast's dynarec on Linux
        pygame.init()
    pygame.joystick.init()
    pad = None
    if pygame.joystick.get_count() > 0:
        pad = pygame.joystick.Joystick(0)
        pad.init()
        print(f"[play] gamepad: {pad.get_name()} ({pad.get_numbuttons()} buttons, "
              f"{pad.get_numhats()} hats, {pad.get_numaxes()} axes)")
    padmap = dict(PAD_DEFAULT)
    for kv in filter(None, args.pad_map.split(",")):
        k, v = kv.split("=")
        padmap[k.strip()] = int(v)
    screen = pygame.display.set_mode((w * args.scale, h * args.scale), pygame.HIDDEN if args.hidden else 0)
    pygame.display.set_caption(f"Power Stone 2 — YOU (P1) vs {os.path.basename(args.model)} (P2)  [{args.mode}]")
    clock = pygame.time.Clock()
    buf = np.zeros((h, w, 3), np.uint8)
    state = {"quit": False, "paused": False, "fast": args.speed == 0}

    audio_ring = None
    audio_stream = None
    if not args.no_sound and args.speed == 1.0:
        try:
            import threading
            import sounddevice as sd
            rate = int(emu.get_audio_rate() or 44100)
            lock = threading.Lock()
            ring = np.zeros((0, 2), np.int16)

            def _cb(outdata, frames, t, status):
                nonlocal ring
                with lock:
                    n = min(frames, len(ring))
                    outdata[:n] = ring[:n]
                    ring = ring[n:]
                if n < frames:
                    outdata[n:] = 0
            audio_stream = sd.OutputStream(samplerate=rate, channels=2, dtype="int16", callback=_cb)
            audio_stream.start()

            def push_audio(s):
                nonlocal ring
                if len(s) == 0:
                    return
                with lock:
                    if len(ring) < rate // 10:
                        ring = np.concatenate([ring, s])
            audio_ring = push_audio
            print(f"[play] sound on ({rate} Hz)")
        except Exception as e:
            print(f"[play] sound unavailable ({e}); silent")

    def human_mask():
        m = np.zeros(N_BUTTONS, np.uint8)
        keys = pygame.key.get_pressed()
        for k, rid in KEYMAP.items():
            if keys[k]:
                m[rid] = 1
        if pad is not None:
            if pad.get_numhats() > 0:
                hx, hy = pad.get_hat(0)
                m[R_RIGHT] |= hx > 0; m[R_LEFT] |= hx < 0
                m[R_UP] |= hy > 0; m[R_DOWN] |= hy < 0
            if pad.get_numaxes() >= 2:
                ax, ay = pad.get_axis(0), pad.get_axis(1)
                m[R_RIGHT] |= ax > 0.5; m[R_LEFT] |= ax < -0.5
                m[R_DOWN] |= ay > 0.5; m[R_UP] |= ay < -0.5
            for name, bid in padmap.items():
                if bid < pad.get_numbuttons() and pad.get_button(bid):
                    m[PAD_TO_RETRO[name]] = 1
        return m

    def pump_events():
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                state["quit"] = True
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    state["quit"] = True
                elif ev.key == pygame.K_p:
                    state["paused"] = not state["paused"]
            elif ev.type == pygame.JOYBUTTONDOWN and args.show_pad:
                print(f"[pad] button {ev.button} down")

    def render_one():
        emu.get_frame(buf, w, h)
        surf = pygame.surfarray.make_surface(np.transpose(buf[::-1], (1, 0, 2)))
        if args.scale != 1:
            surf = pygame.transform.scale(surf, (w * args.scale, h * args.scale))
        screen.blit(surf, (0, 0))
        pygame.display.flip()
        if not state["fast"]:
            clock.tick(60 * args.speed)

    orig_run_frames = br.run_frames

    def run_frames_human(n):
        for _ in range(n):
            pump_events()
            if state["quit"]:
                raise KeyboardInterrupt
            while state["paused"]:
                pump_events()
                if state["quit"]:
                    raise KeyboardInterrupt
                clock.tick(30)
            m = human_mask()
            br._held[0] = m
            emu.set_button_mask(m, 0)          # P1 = libretro port 0, every frame
            orig_run_frames(1)
            if audio_ring is not None:
                audio_ring(emu.get_audio())
            render_one()

    br.run_frames = run_frames_human

    bot_w = bot_l = ep = 0
    try:
        while args.episodes == 0 or ep < args.episodes:
            obs = _sl(env.reset()); obs = _fs.reset(obs) if _fs else obs
            runner.reset()                                   # Oct 2: fresh LSTM state every episode
            done, info = False, {}
            while not done:
                action = runner.act(obs, deterministic=not args.stochastic)
                obs, r, done, info = env.step(action)
                obs = _sl(obs); obs = _fs.push(obs) if _fs else obs
            ep += 1
            res = info.get("result", "timeout")
            bot_w += res == "win"
            bot_l += res == "loss"
            print(f"[round {ep}] bot {res}  len={env.steps}  (bot {bot_w}W/{bot_l}L)", flush=True)
            pygame.display.set_caption(f"Power Stone 2 — YOU vs bot [{args.mode}]  round {ep}: bot {res}  (bot {bot_w}W/{bot_l}L)")
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\nplayed {ep} rounds: bot {bot_w}W/{bot_l}L")
        if audio_stream is not None:
            try:
                audio_stream.stop(); audio_stream.close()
            except Exception:
                pass
        pygame.quit()


if __name__ == "__main__":
    main()
