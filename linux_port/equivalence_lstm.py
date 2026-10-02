"""equivalence_lstm.py <parent_zip> <recurrent_zip> [--frames N] [--instance I] — prove surgery_lstm.py
preserved behaviour: on N real frames (lv8 state, episodes with resets), the recurrent policy run with
its LSTM state carried step to step must give the parent's action logits and value to 1e-5, at every
step. The LSTM is live (its state evolves); only its zeroed output columns make it irrelevant."""
import argparse, os
import numpy as np, torch as th
from obs_stack import FrameStack, kd_for
from powerstone_env_libretro import PowerStoneEnvLibretro
from recurrent_policy import load_model

ap = argparse.ArgumentParser(); ap.add_argument("parent"); ap.add_argument("recurrent")
ap.add_argument("--frames", type=int, default=3000); ap.add_argument("--instance", type=int, default=40)
a = ap.parse_args()
P = load_model(a.parent); R = load_model(a.recurrent)
K, d = kd_for(P)
core = os.environ.get("PS2_CORE") or os.path.expanduser("~/cores/flycast_libretro.so")
env = PowerStoneEnvLibretro(core_path=core, game_path="../Power Stone 2 (USA).chd", states_dir="./states",
                            state_slots=[3], instance_id=a.instance, bridge_dir=os.path.abspath(f"./bridge_probe_{a.instance}"))
fs = FrameStack(K, d)
obs = fs.reset(np.asarray(env.reset(), np.float32)[:d])
state, start = None, np.ones((1,), dtype=bool)
worst_logit = worst_val = 0.0; n = agree = eps = 0; hmax = 0.0
with th.no_grad():
    while n < a.frames:
        o = th.as_tensor(obs[None])
        lp = P.policy.get_distribution(o).distribution.logits
        vp = P.policy.predict_values(o)
        if state is None:
            z = np.zeros(R.policy.lstm_hidden_state_shape, np.float32)
            state = (z, z.copy())
        st = (th.as_tensor(state[0]), th.as_tensor(state[1]))
        es = th.as_tensor(start.astype(np.float32))
        dist, new_st = R.policy.get_distribution(o, st, es)
        lr = dist.distribution.logits
        vr = R.policy.predict_values(o, st, es)
        state = (new_st[0].numpy(), new_st[1].numpy()); start = np.zeros((1,), dtype=bool)
        hmax = max(hmax, float(np.abs(state[0]).max()))
        worst_logit = max(worst_logit, float((lp - lr).abs().max())); worst_val = max(worst_val, float((vp - vr).abs().max()))
        agree += int(lp.argmax() == lr.argmax())
        act = int(th.distributions.Categorical(logits=lp).sample())
        o2, r, done, info = env.step(act); n += 1
        if done:
            eps += 1; o2 = env.reset(); obs = fs.reset(np.asarray(o2, np.float32)[:d]); start = np.ones((1,), dtype=bool)
        else:
            obs = fs.push(np.asarray(o2, np.float32)[:d])
print(f"equivalence over {n} frames, {eps} episode resets (K={K} x {d}, LSTM live: max |h| {hmax:.3f}): "
      f"max |logit diff| {worst_logit:.2e}, max |value diff| {worst_val:.2e}, argmax agreement {agree}/{n}")
print("PASS" if worst_logit < 1e-5 and worst_val < 1e-5 and agree == n and hmax > 0 else "FAIL")
raise SystemExit(0 if worst_logit < 1e-5 and worst_val < 1e-5 and agree == n and hmax > 0 else 1)
