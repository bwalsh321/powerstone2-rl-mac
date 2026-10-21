"""surgery_widen_net.py -- one-shot, FUNCTION-PRESERVING widening of the policy/value MLPs (and optionally the LSTMs)
(Oct 14 2026, Blake: "retest a bigger network" -- 512 lost to 256 long ago, before memory and vision existed).

Net2Net-style: every new hidden unit gets small random INCOMING weights and ZERO OUTGOING weights, so the widened
model computes exactly the parent's function at step 0 and training grows the new units from there.

MLP (--width W, the league_surgery.txt kind "widen<W>", e.g. widen512; SB3 MlpExtractor, Tanh, net_arch [256, 256]):
  for each of mlp_extractor.policy_net / value_net, layer l = 0, 2 (Linear) and the heads action_net / value_net:
    * rows (outputs) of the parent's units: the parent's weights in the parent's columns, bit for bit; the columns
      that read NEW units of the layer below are 0.0 (outgoing weights of new units);
    * rows of NEW units: N(0, (init_scale * std of the parent's weight tensor)^2) incoming weights, bias 0.0;
    * heads (action_net [63, W], value_net [1, W]): parent's columns copied, new-unit columns 0.0.
  The old units' pre-activations are therefore the parent's (the extra terms are exactly 0 * h), so logits and value
  are the parent's up to float32 accumulation order.
LSTM (--lstm-hidden H, the kind "lstm<H>", e.g. lstm256; SkipLSTM only, both lstm_actor and lstm_critic):
  for each gate block (i, f, g, o) of weight_ih / weight_hh / biases: the parent's rows for the old units, with the
  weight_hh columns that read NEW units = 0.0; new units' rows small random (biases 0.0). The MLP first layers read
  [features, lstm_out]: the new lstm_out columns are 0.0. Old units' gates/cell/hidden are the parent's; new units'
  hidden state feeds nothing until training moves those zeros.
Optimizer: the parent's Adam state is kept (step count, betas, lr); each widened tensor's exp_avg / exp_avg_sq are
  placed into the new shape with ZERO for every new entry (new rows and the new zero columns). Note: Adam's bias
  correction uses the parent's step (~1e6, i.e. none), so in the first few hundred grad steps a new entry moves up to
  ~3-6x lr per step (m/sqrt(v) of freshly zeroed moments), then settles to the usual ~1x lr.
Unchanged: observation space, action space, LSTM input width, every hyperparameter, num_timesteps, n_updates.

Gates (exit 1 on fail; nothing written):
  (1) STRUCTURE: every parent entry is bit-identical at its new position and every outgoing weight of a new unit is
      exactly 0.0;
  (2) EXACT: widened(x) == parent(x) on random inputs, recurrently over 40 steps (LSTM state carried), relative
      float32 gate REL_TOL = 1e-5 of the output scale (surgery_widen_v4.gate);
  (3) --obs real.npz (stacked obs + episode starts, from `surgery_zero_itememb.py --collect`): run recurrently over
      the real episode boundaries; max |logit| / |value| diff gated the same way, and the top-action agreement is
      reported (expected 100%; a tie within float noise is the only way it can differ).

    python surgery_widen_net.py IN.zip OUT.zip --width 512 [--lstm-hidden 256] [--obs real.npz] [--init-scale 0.1]
    python surgery_widen_net.py --check IN.zip --width 512 [--lstm-hidden 256]   # exit 0 iff the zip already has it

Wired into league_leg_async.sh as the league_surgery.txt kinds "widen<W>" (needs PS2_NET_WIDTH=W in league_env.txt)
and "lstm<H>" for H != 128 (needs PS2_LSTM_HIDDEN=H); the trainer refuses a warm zip whose width disagrees with a set
flag (recurrent_policy.check_net_flags). Loaders never read the flags: the width always comes from the zip.
"""
import argparse
import sys

import gymnasium
import numpy as np
import torch as th

from recurrent_policy import net_widths
from surgery_widen_v4 import REL_TOL, gate, load_any

LIN = (0, 2)                    # Linear layers inside MlpExtractor's Sequential (Tanh at 1, 3)


def _rand(g, shape, ref, scale):
    sd = float(ref.float().std()) if ref.numel() > 1 else 0.05
    return th.as_tensor(g.normal(0.0, scale * sd, shape).astype(np.float32))


def plan_tensor(name, s, t, w_old, w_new, h_old, h_new, D_feat):
    """Index maps for one tensor: (row_index, col_index) = positions in the NEW tensor of the parent's rows / cols;
    entries of the new tensor outside rows x cols are new. Also says which new entries are 'outgoing of a new unit'
    (must be exactly 0) vs 'incoming of a new unit' (small random): out_zero_cols / new_rows."""
    def mlp_rows(n_old, n_new):
        return th.arange(n_old)

    def gate_rows(H_old, H_new):            # LSTM: 4 gate blocks of H rows each
        return th.cat([k * H_new + th.arange(H_old) for k in range(4)])

    if name.startswith("mlp_extractor.") and name.endswith(".weight"):
        layer = int(name.split(".")[2])
        rows = mlp_rows(w_old, w_new)
        if layer == 0:                      # input = [features (D_feat), lstm_out (h)]
            cols = th.cat([th.arange(D_feat), D_feat + th.arange(h_old)]) if h_old else th.arange(D_feat)
        else:
            cols = th.arange(w_old)
        return rows, cols
    if name.startswith("mlp_extractor.") and name.endswith(".bias"):
        return mlp_rows(w_old, w_new), None
    if name in ("action_net.weight", "value_net.weight"):
        return th.arange(s.shape[0]), th.arange(w_old)
    if name in ("action_net.bias", "value_net.bias"):
        return th.arange(s.shape[0]), None
    if name.startswith("lstm_") and "weight_ih" in name:
        return gate_rows(h_old, h_new), th.arange(s.shape[1])
    if name.startswith("lstm_") and "weight_hh" in name:
        return gate_rows(h_old, h_new), th.arange(h_old)
    if name.startswith("lstm_") and "bias" in name:
        return gate_rows(h_old, h_new), None
    raise SystemExit(f"no widening rule for {name} {tuple(s.shape)} -> {tuple(t.shape)}")


def place(s, t_shape, rows, cols, fill):
    """New tensor of t_shape filled from `fill` (a tensor of t_shape), with the parent's s at (rows, cols)."""
    out = fill.clone()
    if cols is None:
        out[rows] = s
    else:
        out[rows.unsqueeze(1), cols.unsqueeze(0)] = s
    return out


def new_fill(name, t_shape, s, rows, cols, g, scale):
    """Fill for the entries the parent does not have: new units' incoming weights random, biases 0, and every
    column that reads a NEW unit (outgoing weight of a new unit) 0."""
    if len(t_shape) == 1:
        return th.zeros(t_shape)
    fill = th.zeros(t_shape)
    new_row = th.ones(t_shape[0], dtype=th.bool)
    new_row[rows] = False
    if new_row.any():                          # incoming weights of new units: random in EVERY column (old + new)
        fill[new_row] = _rand(g, (int(new_row.sum()), t_shape[1]), s, scale)
    return fill                                 # old rows x new cols stay 0.0 (outgoing of new units)


def widen(src, recurrent, width=None, lstm_hidden=None, init_scale=0.1, seed=0):
    w_pi, w_vf, h_old = net_widths(src.policy)
    assert w_pi == w_vf and len(set(w_pi)) == 1, f"expected equal-width pi/vf MLPs, got pi={w_pi} vf={w_vf}"
    w_old = w_pi[0]
    w_new = int(width or w_old)
    h_new = int(lstm_hidden or h_old or 0)
    if w_new < w_old or (h_old and h_new < h_old):
        raise SystemExit(f"this surgery only widens (MLP {w_old}->{w_new}, LSTM {h_old}->{h_new})")
    if lstm_hidden and not recurrent:
        raise SystemExit("--lstm-hidden needs a recurrent (SkipLSTM) zip")
    D_feat = int(src.observation_space.shape[0])

    class SpaceEnv(gymnasium.Env):
        def __init__(self):
            self.observation_space = src.observation_space
            self.action_space = src.action_space

        def reset(self, *, seed=None, options=None):
            return np.zeros(D_feat, np.float32), {}

        def step(self, action):
            return np.zeros(D_feat, np.float32), 0.0, False, False, {}

    pk = dict(src.policy_kwargs or {})
    pk["net_arch"] = [w_new] * len(w_pi)
    if recurrent:
        pk["lstm_hidden_size"] = h_new
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
        dst = PPO("MlpPolicy", SpaceEnv(), seed=seed, **kw)

    g = np.random.default_rng(seed)
    sd_src, sd_dst = src.policy.state_dict(), dst.policy.state_dict()
    assert list(sd_src) == list(sd_dst), "parent and widened policies have different tensor lists"
    new, maps, widened = {}, {}, []
    for name, t in sd_dst.items():
        s = sd_src[name]
        if t.shape == s.shape and not name.startswith("lstm_") and not (name.startswith("mlp_extractor.")
                                                                        and name.endswith(".0.weight")):
            new[name] = s.clone()
            continue
        rows, cols = plan_tensor(name, s, t, w_old, w_new, h_old, h_new, D_feat)
        new[name] = place(s, t.shape, rows, cols, new_fill(name, t.shape, s, rows, cols, g, init_scale))
        maps[name] = (rows, cols)
        if t.shape != s.shape:
            widened.append(name)
    dst.policy.load_state_dict(new)

    # optimizer: parent's state; each widened tensor's moments placed at the parent's positions, new entries 0
    names_s = [n for n, _ in src.policy.named_parameters()]
    names_d = [n for n, _ in dst.policy.named_parameters()]
    assert names_s == names_d, "parameter order differs; cannot map the optimizer state"
    osd = src.policy.optimizer.state_dict()
    shapes = {n: p.shape for n, p in dst.policy.named_parameters()}
    n_moved = 0
    for pi, name in enumerate(names_s):
        st = osd["state"].get(pi)
        if st is None or name not in widened:
            continue
        rows, cols = maps[name]
        osd["state"][pi] = st = dict(st)       # state_dict() shares the per-param dicts: never edit the parent's
        for key in ("exp_avg", "exp_avg_sq"):
            if key in st:
                st[key] = place(st[key], shapes[name], rows, cols, th.zeros(shapes[name]))
                n_moved += 1
    dst.policy.optimizer.load_state_dict(osd)
    dst.num_timesteps = src.num_timesteps
    dst._n_updates = src._n_updates
    info = dict(w_old=w_old, w_new=w_new, h_old=h_old, h_new=h_new, D=D_feat, widened=widened, maps=maps,
                n_moved=n_moved, n_layers=len(w_pi))
    return dst, info


def check_structure(src, dst, info):
    """(parent entries not bit-identical at their new position, outgoing-of-new-unit entries that are not 0.0,
    Adam moment entries that are neither the parent's nor 0.0 for new entries)."""
    sd_s, sd_d = src.policy.state_dict(), dst.policy.state_dict()
    bad_copy = bad_zero = 0
    for name, t in sd_d.items():
        s = sd_s[name]
        if name not in info["maps"]:
            bad_copy += int((t != s).sum())
            continue
        rows, cols = info["maps"][name]
        if cols is None:
            bad_copy += int((t[rows] != s).sum())
            continue
        bad_copy += int((t[rows.unsqueeze(1), cols.unsqueeze(0)] != s).sum())
        newc = th.ones(t.shape[1], dtype=th.bool)
        newc[cols] = False
        bad_zero += int((t[rows][:, newc] != 0).sum())        # old units must not read new units
    # optimizer
    ps, pd = dict(src.policy.named_parameters()), dict(dst.policy.named_parameters())
    bad_opt = 0
    for name in pd:
        a, b = src.policy.optimizer.state.get(ps[name], {}), dst.policy.optimizer.state.get(pd[name], {})
        for key in ("exp_avg", "exp_avg_sq"):
            if key not in a:
                continue
            x, y = a[key], b[key]
            if name not in info["maps"]:
                bad_opt += int((x != y).sum())
                continue
            rows, cols = info["maps"][name]
            mask = th.zeros(y.shape, dtype=th.bool)
            if cols is None:
                bad_opt += int((y[rows] != x).sum()); mask[rows] = True
            else:
                bad_opt += int((y[rows.unsqueeze(1), cols.unsqueeze(0)] != x).sum())
                mask[rows.unsqueeze(1), cols.unsqueeze(0)] = True
            bad_opt += int((y[~mask] != 0).sum())
        if a.get("step") is not None and float(a["step"]) != float(b.get("step", -1)):
            bad_opt += 1
    return bad_copy, bad_zero, bad_opt


def check_equivalence(src, dst, recurrent, D, n=256, T=40, seed=1):
    g = np.random.default_rng(seed)
    sc = {}
    with th.no_grad():
        if not recurrent:
            x = th.as_tensor(g.uniform(-2, 2, (n, D)).astype(np.float32))
            lp = src.policy.get_distribution(x).distribution.logits
            lw = dst.policy.get_distribution(x).distribution.logits
            vp, vw = src.policy.predict_values(x), dst.policy.predict_values(x)
            sc["logit"], sc["value"] = float(lp.abs().max()), float(vp.abs().max())
            return float((lp - lw).abs().max()), float((vp - vw).abs().max()), sc
        from sb3_contrib.common.recurrent.type_aliases import RNNStates

        def zeros(pol):
            hs, nl = pol.lstm_actor.hidden_size, pol.lstm_actor.num_layers
            z = lambda: th.zeros(nl, n, hs)
            return RNNStates((z(), z()), (z(), z()))
        sp, sw = zeros(src.policy), zeros(dst.policy)
        wl = wv = 0.0
        for t in range(T):
            x = th.as_tensor(g.uniform(-2, 2, (n, D)).astype(np.float32))
            start = th.as_tensor(np.full(n, t == 0, np.float32))
            dp, _ = src.policy.get_distribution(x, sp.pi, start)
            dw, _ = dst.policy.get_distribution(x, sw.pi, start)
            vp = src.policy.predict_values(x, sp.vf, start)
            vw = dst.policy.predict_values(x, sw.vf, start)
            _, _, _, sp = src.policy.forward(x, sp, start)
            _, _, _, sw = dst.policy.forward(x, sw, start)
            wl = max(wl, float((dp.distribution.logits - dw.distribution.logits).abs().max()))
            wv = max(wv, float((vp - vw).abs().max()))
            sc["logit"] = max(sc.get("logit", 0.0), float(dp.distribution.logits.abs().max()))
            sc["value"] = max(sc.get("value", 0.0), float(vp.abs().max()))
        return wl, wv, sc


def agreement(src, dst, recurrent, obs_path):
    from surgery_zero_itememb import run_seq
    z = np.load(obs_path)
    obs, starts = z["obs"].astype(np.float32), z["start"].astype(bool)
    assert obs.shape[1] == src.observation_space.shape[0], f"{obs_path}: obs width {obs.shape[1]}"
    lp, vp = run_seq(src, obs, starts, recurrent)
    lw, vw = run_seq(dst, obs, starts, recurrent)
    pp = th.softmax(th.as_tensor(lp), 1).numpy()
    pw = th.softmax(th.as_tensor(lw), 1).numpy()
    r = dict(n=len(obs), starts=int(starts.sum()), top=int((lp.argmax(1) == lw.argmax(1)).sum()),
             dl=float(np.abs(lp - lw).max()), dv=float(np.abs(vp - vw).max()), dp=float(np.abs(pp - pw).max()),
             sc=dict(logit=float(np.abs(lp).max()), value=float(np.abs(vp).max())))
    ok, rl, rv = gate(r["dl"], r["dv"], r["sc"])
    print(f"[wn] real obs ({r['n']} steps, {r['starts']} episode starts, recurrent): top action agrees "
          f"{r['top']}/{r['n']} = {r['top'] / r['n']:.1%}; max |logit diff| {r['dl']:.2e} (rel {rl:.1e}), max |action "
          f"prob diff| {r['dp']:.2e}, max |value diff| {r['dv']:.2e} (rel {rv:.1e}) -> {'PASS' if ok else 'FAIL'}",
          flush=True)
    return ok, r


def has(path, width, lstm_hidden):
    m, _ = load_any(path)
    w_pi, w_vf, h = net_widths(m.policy)
    return ((width is None or set(w_pi + w_vf) == {int(width)}) and
            (lstm_hidden is None or h == int(lstm_hidden)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--width", type=int, default=None, help="MLP hidden width (both layers, policy and value)")
    ap.add_argument("--lstm-hidden", type=int, default=None, help="LSTM hidden size (actor and critic)")
    ap.add_argument("--init-scale", type=float, default=0.1,
                    help="new units' incoming weights ~ N(0, (scale * parent tensor std)^2)")
    ap.add_argument("--obs", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.width is None and a.lstm_hidden is None:
        raise SystemExit("give --width and/or --lstm-hidden")
    if a.check:
        sys.exit(0 if has(a.src, a.width, a.lstm_hidden) else 1)
    if not a.dst:
        raise SystemExit("usage: surgery_widen_net.py IN.zip OUT.zip --width W [--lstm-hidden H]")
    src, rec = load_any(a.src)
    dst, info = widen(src, rec, a.width, a.lstm_hidden, a.init_scale, a.seed)
    if not info["widened"]:
        raise SystemExit(f"{a.src} already has MLP width {info['w_old']} / LSTM {info['h_old']}; nothing to do")
    b_copy, b_zero, b_opt = check_structure(src, dst, info)
    wl, wv, sc = check_equivalence(src, dst, rec, info["D"])
    num_ok, rl, rv = gate(wl, wv, sc)
    ok = num_ok and b_copy == 0 and b_zero == 0 and b_opt == 0
    n_src = sum(p.numel() for p in src.policy.parameters())
    n_dst = sum(p.numel() for p in dst.policy.parameters())
    print(f"[wn] {a.src} ({'SkipLSTM' if rec else 'MLP'}, {info['D']} inputs, MLP {info['n_layers']}x{info['w_old']}"
          f"{', LSTM %d' % info['h_old'] if rec else ''}, {n_src:,} params) -> {a.dst} (MLP {info['n_layers']}x"
          f"{info['w_new']}{', LSTM %d' % info['h_new'] if rec else ''}, {n_dst:,} params); widened {len(info['widened'])} "
          f"tensors; Adam moments placed (new entries 0): {info['n_moved']}; init_scale {a.init_scale}", flush=True)
    print(f"[wn] structure: {b_copy} parent entries moved/changed, {b_zero} non-zero outgoing weights of new units, "
          f"{b_opt} optimizer entries off; exact check (random inputs, recurrent): max |logit diff| {wl:.2e} "
          f"(rel {rl:.1e} of |{sc.get('logit', 0):.1f}|), max |value diff| {wv:.2e} (rel {rv:.1e} of "
          f"|{sc.get('value', 0):.1f}|), rel tol {REL_TOL:.0e} -> {'PASS' if ok else 'FAIL'}", flush=True)
    if a.obs:
        ok_obs, _ = agreement(src, dst, rec, a.obs)
        ok = ok and ok_obs
    if not ok:
        raise SystemExit(1)
    dst.save(a.dst.removesuffix(".zip"))
    print(f"[wn] wrote {a.dst}; num_timesteps={dst.num_timesteps} n_updates={dst._n_updates}", flush=True)
