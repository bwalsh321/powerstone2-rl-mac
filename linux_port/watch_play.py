"""watch_play.py — spectate the model playing, in a real window.

The env drives the game exactly as in eval_parity (same obs, same
deterministic-or-not policy), but every emulated frame is blitted to a
pygame window and paced to real time — so you can SEE what the bot sees
and screen-record it for posterity/reddit.

Keys:  ESC / close window = quit    SPACE = pause    F = fast (no pacing)

Usage (linux_port/, venv active):
    SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. python -u watch_play.py \
        --core "$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" \
        --game "../Power Stone 2 (USA).chd" --slot 2
Options: --model <zip> (default legG warm-start copy)  --episodes N
         --stochastic (sample actions)  --scale 2  --speed 1.0
"""
import argparse
import os

import numpy as np
import pygame

from stable_baselines3 import PPO

from powerstone_env_libretro import PowerStoneEnvLibretro


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--model", default="./powerstone_v6_ppo.zip")
    ap.add_argument("--states", default="./states")
    ap.add_argument("--slot", type=int, default=2)
    ap.add_argument("--episodes", type=int, default=0, help="0 = until quit")
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--speed", type=float, default=1.0,
                    help="pacing multiplier; 0 = uncapped")
    args = ap.parse_args()

    env = PowerStoneEnvLibretro(
        core_path=args.core, game_path=args.game, states_dir=args.states,
        state_slots=[args.slot])
    model = PPO.load(args.model.removesuffix(".zip"), device="cpu")

    br = env._lr_bridge
    emu = br.emu
    h, w = emu.get_shape()
    pygame.init()
    screen = pygame.display.set_mode((w * args.scale, h * args.scale))
    pygame.display.set_caption("Power Stone 2 — legG spectator")
    clock = pygame.time.Clock()
    buf = np.zeros((h, w, 3), np.uint8)
    state = {"quit": False, "paused": False, "fast": args.speed == 0}

    def pump_events():
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                state["quit"] = True
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    state["quit"] = True
                elif ev.key == pygame.K_SPACE:
                    state["paused"] = not state["paused"]
                elif ev.key == pygame.K_f:
                    state["fast"] = not state["fast"]

    def render_one():
        emu.get_frame(buf, w, h)
        # GL reads frames bottom-up -> flip vertically for display
        surf = pygame.surfarray.make_surface(
            np.transpose(buf[::-1], (1, 0, 2)))
        if args.scale != 1:
            surf = pygame.transform.scale(
                surf, (w * args.scale, h * args.scale))
        screen.blit(surf, (0, 0))
        pygame.display.flip()
        if not state["fast"]:
            clock.tick(60 * args.speed)

    # Render every emulated frame: wrap the bridge's run_frames so ALL
    # paths (actions, intro pumps, stale-read pumps) draw and pace.
    orig_run_frames = br.run_frames

    def run_frames_rendered(n):
        for _ in range(n):
            pump_events()
            if state["quit"]:
                raise KeyboardInterrupt
            while state["paused"]:
                pump_events()
                if state["quit"]:
                    raise KeyboardInterrupt
                clock.tick(30)
            orig_run_frames(1)
            render_one()

    br.run_frames = run_frames_rendered

    wins = losses = ep = 0
    try:
        while args.episodes == 0 or ep < args.episodes:
            obs = env.reset()
            done, info = False, {}
            while not done:
                action, _ = model.predict(
                    obs, deterministic=not args.stochastic)
                obs, r, done, info = env.step(action)
            ep += 1
            res = info.get("result", "timeout")
            wins += res == "win"
            losses += res == "loss"
            pygame.display.set_caption(
                f"Power Stone 2 — legG spectator  |  ep {ep}: {res}  "
                f"({wins}W/{losses}L)")
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\nwatched {ep} episodes: {wins}W/{losses}L")
        pygame.quit()
        env.close()


if __name__ == "__main__":
    main()
