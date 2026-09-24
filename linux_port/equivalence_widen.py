"""equivalence_widen.py <parent_zip> <widened_zip> [--frames N] [--instance I] — run under PS2_OBS_V3=1
PS2_OBS_V2=1. On N real steps from the lv8 state (obs v3, 160/frame), the widened policy fed the
v3 obs with the NEW dims zeroed must equal the parent fed obs[:122] (logits and value to 1e-5).
Also reports the widened policy's argmax agreement on the REAL v3 obs (expected < 100%: the new
dims are zero-weighted, so any difference comes only from the projectile slots reordering)."""
import argparse, os, numpy as np, torch as th
from stable_baselines3 import PPO
from obs_stack import kd_for, FrameStack
from powerstone_env_libretro import PowerStoneEnvLibretro
ap = argparse.ArgumentParser(); ap.add_argument("parent"); ap.add_argument("widened")
ap.add_argument("--frames", type=int, default=2000); ap.add_argument("--instance", type=int, default=12)
a = ap.parse_args()
assert os.environ.get("PS2_OBS_V3") == "1"
P = PPO.load(a.parent.removesuffix(".zip"), device="cpu"); W = PPO.load(a.widened.removesuffix(".zip"), device="cpu")
kp, dp = kd_for(P); kw_, dw = kd_for(W); assert kp == kw_ and dp == 122 and dw == 160
core = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
env = PowerStoneEnvLibretro(core_path=core, game_path="../Power Stone 2 (USA).chd", states_dir="./states",
                            state_slots=[3], instance_id=a.instance, bridge_dir=os.path.abspath(f"./bridge_probe_{a.instance}"))
assert env.OBS_DIM == 160
fp, fz, fw = FrameStack(kp, 122), FrameStack(kp, 160), FrameStack(kp, 160)
obs = env.reset(); op = fp.reset(obs[:122]); oz = fz.reset(np.concatenate([obs[:122], np.zeros(38, np.float32)])); ow = fw.reset(obs)
worst_l = worst_v = 0.0; n = 0; agree_z = agree_w = 0; nz_new = 0
with th.no_grad():
    while n < a.frames:
        lp = P.policy.get_distribution(th.as_tensor(op[None])).distribution.logits
        lz = W.policy.get_distribution(th.as_tensor(oz[None])).distribution.logits
        lw = W.policy.get_distribution(th.as_tensor(ow[None])).distribution.logits
        vp = P.policy.predict_values(th.as_tensor(op[None])); vz = W.policy.predict_values(th.as_tensor(oz[None]))
        worst_l = max(worst_l, float((lp - lz).abs().max())); worst_v = max(worst_v, float((vp - vz).abs().max()))
        agree_z += int(lp.argmax() == lz.argmax()); agree_w += int(lp.argmax() == lw.argmax())
        nz_new += int(np.abs(obs[122:]).sum() > 0)
        act, _ = W.predict(ow, deterministic=False)
        obs, r, done, info = env.step(act); n += 1
        if done:
            obs = env.reset(); op = fp.reset(obs[:122]); oz = fz.reset(np.concatenate([obs[:122], np.zeros(38, np.float32)])); ow = fw.reset(obs)
        else:
            op = fp.push(obs[:122]); oz = fz.push(np.concatenate([obs[:122], np.zeros(38, np.float32)])); ow = fw.push(obs)
print(f"widen equivalence over {n} steps (K={kp}): max |logit diff| {worst_l:.2e}, max |value diff| {worst_v:.2e}, "
      f"argmax agreement (new dims zeroed) {agree_z}/{n}; agreement on REAL v3 obs {agree_w}/{n}; steps with non-zero v3 block {nz_new}/{n}")
print("PASS" if worst_l < 1e-4 and worst_v < 1e-4 and agree_z == n else "FAIL")   # 1e-4: float32 noise over 1,120 inputs (measured 1.1e-5)
