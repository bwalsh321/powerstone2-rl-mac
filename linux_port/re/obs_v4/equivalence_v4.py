"""equivalence_v4.py <parent_zip> <widened_zip> [--zero-item-emb] [--steps N] [--slot S] [--instance I] -- LIVE check
of surgery_widen_v4.py (the equivalence_widen.py pattern, for obs v4). Run with PS2_OBS_V2=1 PS2_OBS_V3=1.

On N real steps from the v4 env (obs_v4_envpatch mixin on PowerStoneEnvLibretro, ITEMEMB forced to "keep" so the
real v3 prefix is available), the widened policy acts and three streams are evaluated every step:
  W   widened(v4 obs, with obs[12..17] zeroed when --zero-item-emb)
  Pe  parent(obs[:160] per frame, with obs[12..17] zeroed when --zero-item-emb)   -> must equal W (1e-4)
  Pr  parent(obs[:160] per frame, real)                                           -> greedy agreement reported
Feed-forward (stacked) and SkipLSTM models; recurrent streams keep their own LSTM state.
PASS = max |logit diff| and |value diff| between W and Pe < 1e-4 over all steps.
"""
import argparse
import os
import sys

import numpy as np
import torch as th

HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, LP)
os.environ["PS2_OBS_V4_ITEMEMB"] = "keep"           # the env keeps the hash; the streams zero it themselves

ap = argparse.ArgumentParser()
ap.add_argument("parent")
ap.add_argument("widened")
ap.add_argument("--zero-item-emb", action="store_true")
ap.add_argument("--steps", type=int, default=600)
ap.add_argument("--slot", type=int, default=3)
ap.add_argument("--instance", type=int, default=8)
a = ap.parse_args()
assert os.environ.get("PS2_OBS_V3") == "1", "run with PS2_OBS_V3=1 PS2_OBS_V2=1"

import obs_v4_reader as V  # noqa: E402
from obs_v4_envpatch import with_obs_v4  # noqa: E402
from surgery_widen_v4 import load_any  # noqa: E402
from obs_stack import FrameStack  # noqa: E402
from powerstone_env_libretro import PowerStoneEnvLibretro  # noqa: E402

P, rp = load_any(a.parent)
W, rw = load_any(a.widened)
assert rp == rw
K = int(P.observation_space.shape[0]) // 160
assert int(P.observation_space.shape[0]) == 160 * K and int(W.observation_space.shape[0]) == V.V4_DIM * K


class Stream:
    def __init__(self, m, rec):
        self.m, self.rec = m, rec
        self.reset()

    def reset(self):
        self.state, self.start = None, True

    def __call__(self, x):
        x = th.as_tensor(x[None])
        pol = self.m.policy
        if not self.rec:
            return pol.get_distribution(x).distribution.logits[0], pol.predict_values(x)[0]
        if self.state is None:
            from sb3_contrib.common.recurrent.type_aliases import RNNStates
            hs, nl = pol.lstm_actor.hidden_size, pol.lstm_actor.num_layers
            z = lambda: (th.zeros(nl, 1, hs), th.zeros(nl, 1, hs))  # noqa: E731
            self.state = RNNStates(z(), z())
        st = th.as_tensor(np.array([float(self.start)], np.float32))
        d, _ = pol.get_distribution(x, self.state.pi, st)
        v = pol.predict_values(x, self.state.vf, st)
        _, _, _, self.state = pol.forward(x, self.state, st)
        self.start = False
        return d.distribution.logits[0], v[0]


core = os.environ.get("PS2_CORE") or os.path.expanduser(
    "~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" if sys.platform == "darwin"
    else "~/cores/flycast_libretro.so")
Env = with_obs_v4(PowerStoneEnvLibretro)
env = Env(core_path=core, game_path=os.path.join(LP, "..", "Power Stone 2 (USA).chd"),
          states_dir=os.path.join(LP, "states"), state_slots=[a.slot], instance_id=a.instance,
          bridge_dir=os.path.join(os.environ.get("TMPDIR", "/tmp"), f"bridge_eqv4_{a.instance}"))
env.set_action_mode(int(W.action_space.n))


def views(obs):
    z = obs.copy()
    if a.zero_item_emb:
        z[12:18] = 0.0
    return z, z[:160], obs[:160]


fw, fe, fr = FrameStack(K, V.V4_DIM), FrameStack(K, 160), FrameStack(K, 160)
sw, se, sr = Stream(W, rw), Stream(P, rp), Stream(P, rp)
obs = env.reset()
w, e, r = views(obs)
xw, xe, xr = fw.reset(w), fe.reset(e), fr.reset(r)
worst_l = worst_v = 0.0
agree_e = agree_r = n = nz_new = 0
with th.no_grad():
    while n < a.steps:
        lw, vw = sw(xw)
        le, ve = se(xe)
        lr_, _ = sr(xr)
        worst_l = max(worst_l, float((lw - le).abs().max()))
        worst_v = max(worst_v, float((vw - ve).abs().max()))
        agree_e += int(lw.argmax() == le.argmax())
        agree_r += int(lw.argmax() == lr_.argmax())
        nz_new += int(np.abs(obs[160:]).sum() > 0)
        act = int(th.distributions.Categorical(logits=lw).sample())
        obs, rew, done, info = env.step(act)
        n += 1
        w, e, r = views(obs)
        if done:
            obs = env.reset()
            w, e, r = views(obs)
            xw, xe, xr = fw.reset(w), fe.reset(e), fr.reset(r)
            sw.reset(); se.reset(); sr.reset()
        else:
            xw, xe, xr = fw.push(w), fe.push(e), fr.push(r)
ok = worst_l < 1e-4 and worst_v < 1e-4 and agree_e == n
print(f"v4 widen equivalence over {n} live steps (K={K}, {'SkipLSTM' if rw else 'MLP'}, zero_item_emb={a.zero_item_emb}): "
      f"max |logit diff| {worst_l:.2e}, max |value diff| {worst_v:.2e}, greedy agreement vs parent(same prefix) "
      f"{agree_e}/{n}; vs parent on the REAL v3 prefix {agree_r}/{n}; steps with a non-zero v4 block {nz_new}/{n}")
print("PASS" if ok else "FAIL", flush=True)
os._exit(0 if ok else 1)
