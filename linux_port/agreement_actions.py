"""agreement_actions.py <parent_zip> <joint_zip> [--frames N] [--instance I] — measure how the 63-action surgery
changes behaviour on real lv8 frames (Oct 3 2026): legacy argmax preserved (parent action k -> joint
LEGACY_TO_JOINT[k]), probability mass on the 53 new combos, and max |value diff| (must be ~0: the value head
is untouched). Recurrent policies run with their LSTM state carried step to step (both start equal)."""
import argparse, os
import numpy as np, torch as th
from action_space import LEGACY_TO_JOINT, JOINT_N
from obs_stack import FrameStack, kd_for
from powerstone_env_libretro import PowerStoneEnvLibretro
from recurrent_policy import load_model

ap = argparse.ArgumentParser(); ap.add_argument("parent"); ap.add_argument("joint")
ap.add_argument("--frames", type=int, default=2000); ap.add_argument("--instance", type=int, default=43)
a = ap.parse_args()
P = load_model(a.parent); J = load_model(a.joint)
K, d = kd_for(P)
rec = hasattr(P.policy, "lstm_actor")
env = PowerStoneEnvLibretro(core_path=os.path.expanduser("~/cores/flycast_libretro.so"), game_path="../Power Stone 2 (USA).chd",
                            states_dir="./states", state_slots=[90, 91, 92, 93, 94], instance_id=a.instance,
                            bridge_dir=os.path.abspath(f"./bridge_probe_{a.instance}"))
fs = FrameStack(K, d)
obs = fs.reset(np.asarray(env.reset(), np.float32)[:d])
legacy_idx = th.tensor([LEGACY_TO_JOINT[k] for k in range(10)])
combo_mask = th.ones(JOINT_N, dtype=th.bool); combo_mask[legacy_idx] = False
state = None; start = True
agree = n = 0; combo_mass = []; vmax = 0.0
with th.no_grad():
    while n < a.frames:
        o = th.as_tensor(obs[None])
        if rec:
            if state is None:
                z = th.zeros(P.policy.lstm_hidden_state_shape); state = (z, z.clone())
            es = th.tensor([float(start)])
            dp, st_p = P.policy.get_distribution(o, state, es)
            dj, _ = J.policy.get_distribution(o, state, es)
            vp = P.policy.predict_values(o, state, es); vj = J.policy.predict_values(o, state, es)
            state = st_p
        else:
            dp = P.policy.get_distribution(o); dj = J.policy.get_distribution(o)
            vp = P.policy.predict_values(o); vj = J.policy.predict_values(o)
        lp, lj = dp.distribution.logits[0], dj.distribution.logits[0]
        pj = th.softmax(lj, -1)
        agree += int(LEGACY_TO_JOINT[int(lp.argmax())] == int(lj.argmax()))
        combo_mass.append(float(pj[combo_mask].sum()))
        vmax = max(vmax, float((vp - vj).abs().max()))
        act = int(th.distributions.Categorical(logits=lp).sample())
        o2, r, done, info = env.step(act); n += 1; start = False
        if done:
            o2 = env.reset(); obs = fs.reset(np.asarray(o2, np.float32)[:d]); start = True
        else:
            obs = fs.push(np.asarray(o2, np.float32)[:d])
cm = np.array(combo_mass)
print(f"agreement over {n} frames ({'recurrent' if rec else 'MLP'}): legacy argmax kept {agree}/{n} = {100*agree/n:.2f}%; "
      f"combo mass mean {100*cm.mean():.2f}% (p50 {100*np.median(cm):.2f}%, p95 {100*np.percentile(cm,95):.2f}%); "
      f"max |value diff| {vmax:.2e}")
