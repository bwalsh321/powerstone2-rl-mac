"""equivalence_v4.py <parent_zip> <widened_zip> [--zero-item-emb] [--steps N] [--slots 90,91] [--states DIR]
[--instance I] -- LIVE exact-warm-start check of surgery_widen_v4.py on the PRODUCTION env (Oct 5 2026; the
re/obs_v4/equivalence_v4.py pattern, but through powerstone_env_v6 with PS2_OBS_V4=1 instead of the envpatch mixin).

On real v4 observations (the new columns LIVE) the widened policy acts and three streams are evaluated every step:
  W   widened(v4 obs, obs[12..17] zeroed when --zero-item-emb)
  Pe  parent(obs[:160] per frame, obs[12..17] zeroed when --zero-item-emb)   -> must equal W
  Pr  parent(obs[:160] per frame, real)                                      -> greedy agreement reported
Recurrent streams keep their own LSTM state; episodes cycle over --slots. PASS = surgery_widen_v4.gate (max |diff| /
max(1, max |parent output|) < 1e-5 for logits and values) and greedy agreement W vs Pe N/N.
Run with PS2_OBS_V2=1 PS2_OBS_V3=1 (PS2_OBS_V4=1 is forced here; the env keeps the hash, streams zero it themselves).
"""
import argparse
import os
import random
import sys

import numpy as np
import torch as th

os.environ["PS2_OBS_V4"] = "1"
os.environ["PS2_OBS_V4_ITEMEMB"] = "keep"

ap = argparse.ArgumentParser()
ap.add_argument("parent")
ap.add_argument("widened")
ap.add_argument("--zero-item-emb", action="store_true")
ap.add_argument("--steps", type=int, default=600)
ap.add_argument("--slots", default="90,91,92,93,94")
ap.add_argument("--states", default="./states")
ap.add_argument("--instance", type=int, default=60)
ap.add_argument("--game", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Power Stone 2 (USA).chd"))
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()
assert os.environ.get("PS2_OBS_V3") == "1", "run with PS2_OBS_V3=1 PS2_OBS_V2=1"

from obs_stack import FrameStack, kd_for  # noqa: E402
from powerstone_env_libretro import PowerStoneEnvLibretro  # noqa: E402
from surgery_widen_v4 import REL_TOL, load_any  # noqa: E402

random.seed(a.seed)
th.manual_seed(a.seed)
P, rp = load_any(a.parent)
W, rw = load_any(a.widened)
assert rp == rw
(K, dp), (Kw, dw) = kd_for(P), kd_for(W)
assert dp == 160 and dw == 430 and K == Kw, (K, dp, Kw, dw)


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


slots = [int(s) for s in a.slots.split(",")]
env = PowerStoneEnvLibretro(core_path=os.environ["PS2_CORE"], game_path=a.game, states_dir=a.states,
                            state_slots=[slots[0]], instance_id=a.instance,
                            bridge_dir=os.path.abspath(f"bridge_i{a.instance}"))
env.set_action_mode(int(W.action_space.n))
assert env.OBS_DIM == 430


def views(obs):
    z = obs.copy()
    if a.zero_item_emb:
        z[12:18] = 0.0
    return z, z[:160], obs[:160]


fw, fe, fr = FrameStack(K, 430), FrameStack(K, 160), FrameStack(K, 160)
sw, se, sr = Stream(W, rw), Stream(P, rp), Stream(P, rp)
ep = 0
env.STATE_SLOTS = [slots[ep % len(slots)]]
obs = env.reset()
w, e, r = views(obs)
xw, xe, xr = fw.reset(w), fe.reset(e), fr.reset(r)
worst_l = worst_v = scale_l = scale_v = 0.0
agree_e = agree_r = n = nz_new = 0
live_cols = np.zeros(270, bool)
with th.no_grad():
    while n < a.steps:
        lw, vw = sw(xw)
        le, ve = se(xe)
        lr_, _ = sr(xr)
        worst_l = max(worst_l, float((lw - le).abs().max()))
        worst_v = max(worst_v, float((vw - ve).abs().max()))
        scale_l, scale_v = max(scale_l, float(le.abs().max())), max(scale_v, float(ve.abs().max()))
        agree_e += int(lw.argmax() == le.argmax())
        agree_r += int(lw.argmax() == lr_.argmax())
        nz_new += int(np.abs(obs[160:]).sum() > 0)
        live_cols |= obs[160:] != 0
        act = int(th.distributions.Categorical(logits=lw).sample())
        obs, rew, done, info = env.step(act)
        n += 1
        w, e, r = views(obs)
        if done:
            ep += 1
            env.STATE_SLOTS = [slots[ep % len(slots)]]
            obs = env.reset()
            w, e, r = views(obs)
            xw, xe, xr = fw.reset(w), fe.reset(e), fr.reset(r)
            sw.reset(); se.reset(); sr.reset()
        else:
            xw, xe, xr = fw.push(w), fe.push(e), fr.push(r)
rl, rv = worst_l / max(1.0, scale_l), worst_v / max(1.0, scale_v)
ok = rl < REL_TOL and rv < REL_TOL and agree_e == n
print(f"v4 widen equivalence over {n} live steps, {ep + 1} episodes on slots {slots} (K={K}, "
      f"{'SkipLSTM' if rw else 'MLP'}, zero_item_emb={a.zero_item_emb}, obj_grid_n={os.environ.get('PS2_OBJ_GRID_N', '110')}): "
      f"max |logit diff| {worst_l:.2e} (rel {rl:.1e} of |{scale_l:.1f}|), max |value diff| {worst_v:.2e} "
      f"(rel {rv:.1e} of |{scale_v:.1f}|), greedy agreement vs parent(same prefix) {agree_e}/{n}; vs parent on the "
      f"REAL v3 prefix {agree_r}/{n}; steps with a non-zero v4 block {nz_new}/{n}, v4 columns ever live "
      f"{int(live_cols.sum())}/270")
print("PASS" if ok else "FAIL", flush=True)
os._exit(0 if ok else 1)
