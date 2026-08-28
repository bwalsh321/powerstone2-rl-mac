"""Obs-fidelity probe for the P1 self-play view (fix #7 follow-up).

Steps the SelfPlayEnv with random learner actions and, every few steps,
compares BOTH views against ground truth parsed straight from each
synth's line:
  * P1 view self block  vs players[0] (pos, health)
  * P1 view opp block   vs players[1] (the learner)
  * learner view self   vs players[1] (reference — known-good path)
Also runs the frozen 31.9M policy on both views and prints the action
histograms: a broken view usually pins the policy to one action.

Usage: SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. python -u obs_probe.py
"""
import os
import random

import numpy as np
from stable_baselines3 import PPO

from powerstone_env_v6 import POS_SCALE
from selfplay_env import SelfPlayEnv

ROOT = os.path.dirname(os.path.abspath(__file__))
OPP_ZIP = os.path.join(ROOT, "opponent_pool/ps_v6_31915459_steps.zip")


def main():
    core = os.path.expanduser(
        "~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
    game = os.path.join(ROOT, "../Power Stone 2 (USA).chd")
    env = SelfPlayEnv(core_path=core, game_path=game,
                      states_dir=os.path.join(ROOT, "states"),
                      instance_id=5, state_slots=[1],
                      bridge_dir=os.path.join(ROOT, "bridge_probe"),
                      pool_dir=os.path.join(ROOT, "pool_ab"))
    frozen = PPO.load(OPP_ZIP.removesuffix(".zip"), device="cpu")

    obs = env.reset()

    print("=== line diff (learner synth vs opp synth), one frame ===")
    l_lr = env._lr_synth.line.split(",")
    l_op = env._opp_synth.line.split(",")
    print(f"fields: lr={len(l_lr)} opp={len(l_op)}")
    for i, (a, b) in enumerate(zip(l_lr, l_op)):
        if a != b:
            print(f"  field[{i}]: lr={a}  opp={b}")

    acts_lr, acts_op = [], []
    opp0 = env._OPP0 if hasattr(env, "_OPP0") else 18
    for t in range(60):
        o_op = env._obs_from_view(env._opp_synth, agent_player=1)
        s = env._parse_line(env._lr_synth.line)

        a_lr, _ = frozen.predict(obs, deterministic=False)
        a_op, _ = frozen.predict(o_op, deterministic=False)
        acts_lr.append(int(a_lr)); acts_op.append(int(a_op))

        if t % 10 == 0 and s is not None:
            h = [x / 1000.0 for x in s["h"][:2]]
            p0 = s["players"][0]["pos"]; p1 = s["players"][1]["pos"]
            print(f"\n-- t={t} truth: h={h[0]:.2f}/{h[1]:.2f} "
                  f"P1=({p0[0]:.0f},{p0[2]:.0f}) P2=({p1[0]:.0f},{p1[2]:.0f})")
            print(f"   P1view self : h={o_op[0]:.2f} "
                  f"pos=({o_op[1]*POS_SCALE:.0f},{o_op[2]*POS_SCALE:.0f})")
            print(f"   P1view opp0 : present={o_op[opp0]:.0f} "
                  f"d=({o_op[opp0+1]*POS_SCALE:.0f},{o_op[opp0+2]*POS_SCALE:.0f}) "
                  f"h={o_op[opp0+7]:.2f}  "
                  f"truth dP2-P1=({p1[0]-p0[0]:.0f},{p1[2]-p0[2]:.0f})")
            print(f"   LRview self : h={obs[0]:.2f} "
                  f"pos=({obs[1]*POS_SCALE:.0f},{obs[2]*POS_SCALE:.0f})")
            print(f"   LRview opp0 : present={obs[opp0]:.0f} "
                  f"d=({obs[opp0+1]*POS_SCALE:.0f},{obs[opp0+2]*POS_SCALE:.0f}) "
                  f"h={obs[opp0+7]:.2f}  "
                  f"truth dP1-P2=({p0[0]-p1[0]:.0f},{p0[2]-p1[2]:.0f})")
        obs, _r, done, _info = env.step(random.randrange(10))
        if done:
            obs = env.reset()

    def hist(a):
        u = sorted(set(a))
        return {k: a.count(k) for k in u}
    print(f"\nfrozen-policy action hist on LEARNER view: {hist(acts_lr)}")
    print(f"frozen-policy action hist on P1 view     : {hist(acts_op)}")


if __name__ == "__main__":
    main()
