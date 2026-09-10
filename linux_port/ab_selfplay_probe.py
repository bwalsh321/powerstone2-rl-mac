"""A/B probe: warm-start learner (P2) vs ONE chosen frozen opponent (P1)
through SelfPlayEnv — the discriminator for "is the P1 view/seat
structurally handicapped, or is the pool just full of weak relics?".

Usage:
  SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. python -u \
      ab_selfplay_probe.py --opp opponent_pool/ps_v6_31915459_steps.zip \
      --episodes 12

Learner stochastic (training-like), opponent stochastic (training
default). ~50-70% learner win vs a 27.9-31.9M peer = healthy self-play;
~95%+ = suspect the P1 seat (obs view, savestate character, input path).
Results also land in bridge_ab/ep_stats_v6.csv.
"""
import argparse
import os
import shutil

from stable_baselines3 import PPO

from selfplay_env import SelfPlayEnv

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opp", required=True, help="single opponent zip")
    ap.add_argument("--episodes", type=int, default=12)
    ap.add_argument("--model", default=os.path.join(ROOT, "powerstone_v6_ppo.zip"))
    ap.add_argument("--instance", type=int, default=5,
                    help="emu instance id (system/dolphin-N must exist)")
    args = ap.parse_args()

    core = os.environ.get("PS2_CORE", os.path.expanduser(
        "~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"))
    game = os.environ.get("PS2_GAME", os.path.join(ROOT, "../Power Stone 2 (USA).chd"))

    pool_ab = os.path.join(ROOT, "pool_ab")
    shutil.rmtree(pool_ab, ignore_errors=True)
    os.makedirs(pool_ab)
    shutil.copy(args.opp, pool_ab)

    env = SelfPlayEnv(core_path=core, game_path=game,
                      states_dir=os.path.join(ROOT, "states"),
                      instance_id=args.instance, state_slots=[1],
                      bridge_dir=os.path.join(ROOT, "bridge_ab"),
                      pool_dir=pool_ab)
    model = PPO.load(args.model.removesuffix(".zip"), device="cpu")
    print(f"[ab] model={os.path.basename(args.model)} "
          f"opp={os.path.basename(args.opp)} episodes={args.episodes} "
          f"seats=learner:P2 opponent:P1 (one-seat probe; see HANDOFF "
          f"'AB probes are one-seat')")

    wins = losses = 0
    for ep in range(args.episodes):
        obs = env.reset()
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=False)
            obs, _r, done, info = env.step(action)
        res = info.get("result", "?")
        wins += res == "win"
        losses += res == "loss"
        print(f"[ab] ep {ep + 1}/{args.episodes}: {res}  "
              f"running {wins}W/{losses}L")
    print(f"AB RESULT vs {os.path.basename(args.opp)}: "
          f"{wins}W/{losses}L/{args.episodes - wins - losses}T")


if __name__ == "__main__":
    main()
