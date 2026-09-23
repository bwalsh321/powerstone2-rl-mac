"""equivalence_stack.py <parent_zip> <stacked_zip> [--frames N] [--instance I] — prove the
surgery preserved behaviour: on N real frames from the lv8 state, the stacked policy (fed the
current frame in the newest slot and RANDOM junk in the older slots) must produce the same
action logits and value as the parent, to 1e-5."""
import argparse, os, numpy as np, torch as th
from stable_baselines3 import PPO
from obs_stack import k_for
from powerstone_env_libretro import PowerStoneEnvLibretro
ap = argparse.ArgumentParser(); ap.add_argument("parent"); ap.add_argument("stacked")
ap.add_argument("--frames", type=int, default=3000); ap.add_argument("--instance", type=int, default=13)
a = ap.parse_args()
P = PPO.load(a.parent.removesuffix(".zip"), device="cpu"); S = PPO.load(a.stacked.removesuffix(".zip"), device="cpu")
k = k_for(S); d = P.observation_space.shape[0]
core = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
env = PowerStoneEnvLibretro(core_path=core, game_path="../Power Stone 2 (USA).chd", states_dir="./states",
                            state_slots=[3], instance_id=a.instance, bridge_dir=os.path.abspath(f"./bridge_probe_{a.instance}"))
rng = np.random.default_rng(0)
obs = env.reset(); worst_logit = worst_val = 0.0; n = 0; agree = 0
with th.no_grad():
    while n < a.frames:
        o = np.asarray(obs, np.float32)
        junk = rng.uniform(-5, 5, size=d * (k - 1)).astype(np.float32)
        so = np.concatenate([junk, o])
        lp = P.policy.get_distribution(th.as_tensor(o[None])).distribution.logits
        ls = S.policy.get_distribution(th.as_tensor(so[None])).distribution.logits
        vp = P.policy.predict_values(th.as_tensor(o[None])); vs = S.policy.predict_values(th.as_tensor(so[None]))
        worst_logit = max(worst_logit, float((lp - ls).abs().max())); worst_val = max(worst_val, float((vp - vs).abs().max()))
        agree += int(lp.argmax() == ls.argmax())
        act, _ = P.predict(o, deterministic=False)
        obs, r, done, info = env.step(act); n += 1
        if done: obs = env.reset()
print(f"equivalence over {n} frames (K={k}, junk history): max |logit diff| {worst_logit:.2e}, max |value diff| {worst_val:.2e}, argmax agreement {agree}/{n}")
print("PASS" if worst_logit < 1e-5 and worst_val < 1e-5 and agree == n else "FAIL")
