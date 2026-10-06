"""surgery_widen_v4.py <in_zip> <out_zip> [--dim-in 160] [--dim-out 430] [--zero-item-emb] — PROPOSED (obs v4).

Widen a (stacked) PPO MLP policy OR a SkipLSTM RecurrentPPO policy from dim-in to dim-out inputs per frame
WITHOUT changing its behaviour (the surgery_widen.py / surgery_lstm.py pattern):
  * every first-layer weight that reads the stacked observation (mlp_extractor.{policy,value}_net.0.weight;
    for SkipLSTM also the trailing lstm_out columns) gets the parent's columns for each lag slot copied into
    the first dim-in positions of that slot; the new v4 columns start at ZERO;
  * SkipLSTM only: lstm_actor / lstm_critic weight_ih_l0 (they read the NEWEST frame, lstm_input_dim) are
    widened the same way (new columns zero) and lstm_input_dim becomes dim-out;
  * biases, hidden layers, heads, LSTM recurrent weights: copied verbatim; hyperparameters, num_timesteps and
    n_updates carried over (the optimizer state starts fresh, as in every earlier surgery).
Because the new columns are zero, the widened policy's logits and value are a function of obs[:dim-in] per lag
ONLY, for ANY values in the new dims: exact equivalence, checked at the end on random inputs (and, for a live
check, with equivalence_v4.py's pattern in INTEGRATION.md).

--zero-item-emb: ALSO zero the parent's columns for obs[12..17] (the slot-hash "item embedding", which encodes an
arena slot, not an item; GROUND.md 0.4 / ITEMS.md 0). Use it together with the env flag that writes zeros there
(PS2_OBS_V4_ITEMEMB=zero). The widened policy then equals the parent evaluated with obs[12..17] = 0, which is NOT
bit-identical to the parent on real frames: measure the change first with measure_item_emb.py.

Wired into league_leg_async.sh as the league_surgery.txt kind "obsv4" (Oct 5 2026; production copy of
re/obs_v4/surgery_widen_v4.py).

PASS gate (Oct 5 2026, replaces the flat 1e-4): (1) STRUCTURAL exactness -- every copied column is bit-identical to
the parent's and every new column is exactly 0.0 (so the widened net computes the same real-number function);
(2) NUMERICAL: max |diff| / max(1, max |parent output|) < 1e-5 for logits and values. Why relative: the residual is
float32 accumulation-order noise of a 3010-wide vs 1120-wide matmul, which scales with the output magnitude; on
leg 127 with random inputs U(-2,2) in all 3010 dims the values reach |74| and the absolute value diff was 7.3e-5
(relative 1e-6, ~8 float32 ulps of 74), within a hair of the old flat 1e-4 although the surgery is exact.
"""
import argparse

import gymnasium
import numpy as np
import torch as th

ITEM_EMB = slice(12, 18)


def load_any(path):
    p = path.removesuffix(".zip")
    try:
        from recurrent_policy import CUSTOM_OBJECTS, is_recurrent_zip
    except ImportError:                       # Mac venv without sb3_contrib: feed-forward only
        CUSTOM_OBJECTS, is_recurrent_zip = {"clip_range": 0.2, "lr_schedule": lambda _: 2.5e-4}, (lambda _: False)
    if is_recurrent_zip(p):
        from sb3_contrib import RecurrentPPO
        return RecurrentPPO.load(p, device="cpu", custom_objects=CUSTOM_OBJECTS), True
    from stable_baselines3 import PPO
    return PPO.load(p, device="cpu", custom_objects=CUSTOM_OBJECTS), False


def widen(src, recurrent, d_in, d_out, zero_item=False, seed=0):
    D_src = int(src.observation_space.shape[0])
    hid = 0
    if recurrent:
        hid = int(src.policy.lstm_output_dim)
        lid = getattr(src.policy, "lstm_input_dim", None) or int(src.policy.lstm_actor.input_size)
        assert lid == d_in, f"source LSTM reads {lid} inputs, expected the newest frame ({d_in})"
    assert D_src % d_in == 0, f"source obs {D_src} is not K x {d_in}"
    K = D_src // d_in
    D = K * d_out

    class SpaceEnv(gymnasium.Env):
        def __init__(self):
            self.observation_space = gymnasium.spaces.Box(-5.0, 5.0, (D,), np.float32)
            self.action_space = gymnasium.spaces.Discrete(int(src.action_space.n))

        def reset(self, *, seed=None, options=None):
            return np.zeros(D, np.float32), {}

        def step(self, action):
            return np.zeros(D, np.float32), 0.0, False, False, {}

    pk = dict(src.policy_kwargs or {})
    if recurrent:
        pk["lstm_input_dim"] = d_out
    kw = dict(learning_rate=src.learning_rate, n_steps=src.n_steps, batch_size=src.batch_size,
              n_epochs=src.n_epochs, gamma=src.gamma, gae_lambda=src.gae_lambda,
              clip_range=src.clip_range(1.0), ent_coef=src.ent_coef, vf_coef=src.vf_coef,
              max_grad_norm=src.max_grad_norm, target_kl=src.target_kl,
              policy_kwargs=pk, device="cpu", verbose=0)
    th.manual_seed(seed)
    if recurrent:
        from sb3_contrib import RecurrentPPO
        dst = RecurrentPPO(type(src.policy), SpaceEnv(), seed=seed, **kw)
    else:
        from stable_baselines3 import PPO
        dst = PPO("MlpPolicy", SpaceEnv(), **kw)

    def map_cols(s):
        """[out, K*d_in (+hid)] -> [out, K*d_out (+hid)], new columns zero."""
        w = th.zeros((s.shape[0], D + hid), dtype=s.dtype)
        for j in range(K):
            blk = s[:, j * d_in:(j + 1) * d_in].clone()
            if zero_item:
                blk[:, ITEM_EMB] = 0.0
            w[:, j * d_out:j * d_out + d_in] = blk
        if hid:
            w[:, D:] = s[:, K * d_in:]
        return w

    sd_src, sd_dst = src.policy.state_dict(), dst.policy.state_dict()
    new, widened = {}, []
    for name, t in sd_dst.items():
        s = sd_src[name]
        if t.shape == s.shape:
            new[name] = s.clone()
            if zero_item and name.endswith(".0.weight") and "mlp_extractor" in name:
                raise SystemExit(f"{name}: shape unchanged although the input widened (dim-in == dim-out?)")
        elif name.endswith(".0.weight") and t.shape[1] == D + hid and s.shape[1] == K * d_in + hid:
            new[name] = map_cols(s)
            widened.append(name)
        elif name.endswith("weight_ih_l0") and t.shape[1] == d_out and s.shape[1] == d_in:
            w = th.zeros_like(t)
            w[:, :d_in] = s
            if zero_item:
                w[:, ITEM_EMB] = 0.0
            new[name] = w
            widened.append(name)
        else:
            raise SystemExit(f"shape mismatch {name}: dst {tuple(t.shape)} src {tuple(s.shape)}")
    missing = [n for n in sd_src if n not in sd_dst]
    assert not missing, f"parent tensors with no home: {missing}"
    dst.policy.load_state_dict(new)
    dst.num_timesteps = src.num_timesteps
    dst._n_updates = src._n_updates
    return dst, K, widened


def check_structure(src, dst, recurrent, K, d_in, d_out, zero_item=False):
    """Number of widened-tensor entries that are NOT an exact copy of the parent (old columns) or exactly 0.0 (new
    columns, and [12..17] under zero_item). 0 = the widened net is the parent's function exactly (real arithmetic)."""
    sd_s, sd_d = src.policy.state_dict(), dst.policy.state_dict()
    D_src = K * d_in
    bad = 0
    for name, t in sd_d.items():
        s = sd_s[name]
        if t.shape == s.shape:
            bad += int((t != s).sum())
            continue
        exp = th.zeros_like(t)
        if name.endswith("weight_ih_l0"):
            exp[:, :d_in] = s
            if zero_item:
                exp[:, ITEM_EMB] = 0.0
        else:
            for j in range(K):
                blk = s[:, j * d_in:(j + 1) * d_in].clone()
                if zero_item:
                    blk[:, ITEM_EMB] = 0.0
                exp[:, j * d_out:j * d_out + d_in] = blk
            exp[:, K * d_out:] = s[:, D_src:]
        bad += int((t != exp).sum())
    return bad


def check_equivalence(src, dst, recurrent, K, d_in, d_out, zero_item=False, n=256, T=40, seed=1, scale=None):
    """Max |logit| and |value| difference between dst(x) and src(x restricted to the parent's columns), with the
    new v4 dims filled with RANDOM values (they must not matter)."""
    g = np.random.default_rng(seed)
    with th.no_grad():
        if not recurrent:
            x = g.uniform(-2, 2, (n, K * d_out)).astype(np.float32)
            xp = np.concatenate([x[:, j * d_out:j * d_out + d_in] for j in range(K)], 1)
            if zero_item:
                for j in range(K):
                    xp[:, j * d_in + 12:j * d_in + 18] = 0.0
            lp = src.policy.get_distribution(th.as_tensor(xp)).distribution.logits
            lw = dst.policy.get_distribution(th.as_tensor(x)).distribution.logits
            vp = src.policy.predict_values(th.as_tensor(xp))
            vw = dst.policy.predict_values(th.as_tensor(x))
            if scale is not None:
                scale["logit"], scale["value"] = float(lp.abs().max()), float(vp.abs().max())
            return float((lp - lw).abs().max()), float((vp - vw).abs().max())
        from sb3_contrib.common.recurrent.type_aliases import RNNStates
        hs = src.policy.lstm_actor.hidden_size
        nl = src.policy.lstm_actor.num_layers

        def zeros():
            z = (th.zeros(nl, n, hs), th.zeros(nl, n, hs))
            return RNNStates(z, (th.zeros(nl, n, hs), th.zeros(nl, n, hs)))
        sp, sw = zeros(), zeros()
        wl = wv = 0.0
        for t in range(T):
            x = g.uniform(-2, 2, (n, K * d_out)).astype(np.float32)
            xp = np.concatenate([x[:, j * d_out:j * d_out + d_in] for j in range(K)], 1)
            if zero_item:
                for j in range(K):
                    xp[:, j * d_in + 12:j * d_in + 18] = 0.0
            start = th.as_tensor(np.full(n, t == 0, np.float32))
            dp, ap_ = src.policy.get_distribution(th.as_tensor(xp), sp.pi, start)
            dw, aw_ = dst.policy.get_distribution(th.as_tensor(x), sw.pi, start)
            vp = src.policy.predict_values(th.as_tensor(xp), sp.vf, start)
            vw = dst.policy.predict_values(th.as_tensor(x), sw.vf, start)
            # advance critic states the way the rollout does (forward() keeps both)
            _, _, _, sp = src.policy.forward(th.as_tensor(xp), sp, start)
            _, _, _, sw = dst.policy.forward(th.as_tensor(x), sw, start)
            wl = max(wl, float((dp.distribution.logits - dw.distribution.logits).abs().max()))
            wv = max(wv, float((vp - vw).abs().max()))
            if scale is not None:
                scale["logit"] = max(scale.get("logit", 0.0), float(dp.distribution.logits.abs().max()))
                scale["value"] = max(scale.get("value", 0.0), float(vp.abs().max()))
        return wl, wv


REL_TOL = 1e-5


def gate(wl, wv, scale):
    """Relative float32 gate (see the module docstring)."""
    rl, rv = wl / max(1.0, scale.get("logit", 0.0)), wv / max(1.0, scale.get("value", 0.0))
    return rl < REL_TOL and rv < REL_TOL, rl, rv


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--dim-in", type=int, default=160)
    ap.add_argument("--dim-out", type=int, default=430)
    ap.add_argument("--zero-item-emb", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    src, rec = load_any(a.src)
    dst, K, widened = widen(src, rec, a.dim_in, a.dim_out, a.zero_item_emb, a.seed)
    sc = {}
    wl, wv = check_equivalence(src, dst, rec, K, a.dim_in, a.dim_out, a.zero_item_emb, scale=sc)
    nbad = check_structure(src, dst, rec, K, a.dim_in, a.dim_out, a.zero_item_emb)
    num_ok, rl, rv = gate(wl, wv, sc)
    ok = num_ok and nbad == 0
    print(f"widen v4: {a.src} ({'SkipLSTM' if rec else 'MLP'}, K={K}, {a.dim_in}/frame) -> {a.dst} ({a.dim_out}/frame, "
          f"{K * a.dim_out} inputs); widened {widened}; zero_item_emb={a.zero_item_emb}; structure: {nbad} non-exact "
          f"entries; offline equivalence (new dims random): max |logit diff| {wl:.2e} (rel {rl:.1e} of |{sc.get('logit', 0):.1f}|), "
          f"max |value diff| {wv:.2e} (rel {rv:.1e} of |{sc.get('value', 0):.1f}|), rel tol {REL_TOL:.0e} "
          f"-> {'PASS' if ok else 'FAIL'}")
    if not ok:
        raise SystemExit(1)
    dst.save(a.dst.removesuffix(".zip"))
