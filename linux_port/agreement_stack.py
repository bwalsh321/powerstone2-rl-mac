"""agreement_stack.py <src_zip> <dst_zip> [--frames N] [--instance I] — for a surgery between two
STACKED layouts (e.g. K=4 contiguous -> K=6 strided), where exact equality is impossible when a
source lag was remapped, measure agreement on a real trajectory: both models see the same base
frames through their own stackers; report max |logit diff|, argmax agreement, and mean |prob diff|."""
import argparse, os, numpy as np, torch as th
from stable_baselines3 import PPO
from obs_stack import FrameStack, k_for
from powerstone_env_libretro import PowerStoneEnvLibretro
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--frames", type=int, default=2000); ap.add_argument("--instance", type=int, default=13)
a = ap.parse_args()
A = PPO.load(a.src.removesuffix(".zip"), device="cpu"); B = PPO.load(a.dst.removesuffix(".zip"), device="cpu")
from obs_stack import kd_for
fa, fb = FrameStack(*kd_for(A)), FrameStack(*kd_for(B))
core = os.environ.get("PS2_CORE") or os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" if os.uname().sysname == "Darwin" else "~/cores/flycast_libretro.so")
env = PowerStoneEnvLibretro(core_path=core, game_path="../Power Stone 2 (USA).chd", states_dir="./states",
                            state_slots=[3], instance_id=a.instance, bridge_dir=os.path.abspath(f"./bridge_probe_{a.instance}"))
obs = env.reset(); oa, ob = fa.reset(obs), fb.reset(obs)
n = agree = 0; worst = 0.0; pdiff = []
with th.no_grad():
    while n < a.frames:
        la = A.policy.get_distribution(th.as_tensor(oa[None])).distribution.logits
        lb = B.policy.get_distribution(th.as_tensor(ob[None])).distribution.logits
        worst = max(worst, float((la - lb).abs().max())); agree += int(la.argmax() == lb.argmax())
        pdiff.append(float((th.softmax(la, -1) - th.softmax(lb, -1)).abs().mean()))
        act, _ = A.predict(oa, deterministic=False)
        obs, r, done, info = env.step(act); n += 1
        if done:
            obs = env.reset(); oa, ob = fa.reset(obs), fb.reset(obs)
        else:
            oa, ob = fa.push(obs), fb.push(obs)
print(f"agreement over {n} frames: argmax {agree}/{n} ({100*agree/n:.2f}%), max |logit diff| {worst:.3e}, mean |prob diff| {np.mean(pdiff):.2e}")
