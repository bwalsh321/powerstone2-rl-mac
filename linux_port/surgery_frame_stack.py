"""surgery_frame_stack.py -- one-shot "framestack<K>" surgery: NARROW a stacked policy to fewer frames (Oct 13 2026,
queued after the lr 5e-5 test; Blake: "try a stack of 2 -- the LSTM may make the older frames redundant").

Frame order (obs_stack.py): a K-frame policy reads K blocks of the per-frame observation, OLDEST FIRST, NEWEST LAST, at
the lags (decision steps of 0.1 s) of obs_stack.OFFSETS_BY_K[K]:
    K=7 : [16, 8, 4, 3, 2, 1, 0]      (the live lineage: 7 x 430 = 3010 inputs)
    K=2 : [1, 0]                      (2 x 430 = 860 inputs)
Every destination lag must exist in the source, so K=7 -> K=2 keeps source blocks 5 and 6 (lag 1 = the previous
step, lag 0 = the current one): columns 2150..3009 of the 3010. The K=2 env stack (FrameStack(2)) produces exactly
those two blocks, so on the same frames the narrowed net sees the same numbers in the kept columns.

What changes in the zip:
  * mlp_extractor.{policy,value}_net.0.weight: keep the columns of the kept lags (+ the trailing lstm_output columns
    of a SkipLSTM, untouched); the dropped lags' columns are removed (--fold: added onto the nearest kept lag instead,
    an approximation that treats an older frame as equal to the previous one; measured, not the default);
  * the Adam moments (exp_avg, exp_avg_sq) of those two weights are sliced the same way; every other optimizer entry
    (and the step count) is carried over, as surgery_zero_itememb.py does;
  * observation_space: Box(K*d) with the parent's bounds for the kept columns (no input normalisation is stored:
    FlattenExtractor, no VecNormalize);
  * unchanged, bit for bit: biases, hidden layers, heads, the LSTMs (they read only the newest frame,
    lstm_input_dim = d, which is still the last block), hyperparameters, num_timesteps, n_updates.
This is NOT behaviour-preserving (the dropped frames carried information). Gates:
  (1) STRUCTURE: every kept entry is bit-identical to the parent's;
  (2) EXACT on the kept inputs: narrowed(x) == parent(x with the dropped blocks ZERO) (fold: == the block they were
      folded into), recurrently on random inputs; relative float32 gate as in surgery_widen_v4.py;
  (3) --obs real.npz (stacked parent-width obs + episode starts, from surgery_zero_itememb.py --collect): how often
      the narrowed policy's top action equals the parent's, and the policy TV / KL. Reported, not gated.

    python surgery_frame_stack.py IN.zip OUT.zip --k 2 [--fold] [--obs real_obs.npz]
    python surgery_frame_stack.py --check IN.zip --k 2        # exit 0 iff the zip already reads K frames

Wired into league_leg_async.sh as the league_surgery.txt kind "framestack2" (needs PS2_OBS_STACK=2 in
league_env.txt; the trainer asserts the two agree).
"""
import argparse
import os
import sys

import gymnasium
import numpy as np
import torch as th

from obs_stack import OFFSETS_BY_K, kd_for
from surgery_widen_v4 import REL_TOL, gate, load_any


def plan(K_src, k_dst, fold=False):
    """[(dst slot, [src slots])] -- src slot i is lag OFFSETS_BY_K[K_src][i]; with fold, every dropped src lag joins
    the kept lag nearest to it (ties -> the older kept lag)."""
    so, do = OFFSETS_BY_K[K_src], OFFSETS_BY_K[k_dst]
    missing = [L for L in do if L not in so]
    if missing:
        raise SystemExit(f"K={K_src} {so} -> K={k_dst} {do}: destination lags {missing} are not in the source; "
                         f"this surgery only narrows (use surgery_stack.py to add lags)")
    groups = {j: [so.index(L)] for j, L in enumerate(do)}
    dropped = [i for i, L in enumerate(so) if L not in do]
    if fold:
        for i in dropped:
            j = min(range(len(do)), key=lambda jj: (abs(do[jj] - so[i]), -do[jj]))
            groups[j].append(i)
    return [(j, groups[j]) for j in range(len(do))], dropped


def narrow_cols(s, groups, d, D_src, hid):
    """[out, K_src*d (+hid)] -> [out, k*d (+hid)]: kept blocks copied (fold: plus their folded blocks)."""
    blocks = []
    for _, src_slots in groups:
        b = s[:, src_slots[0] * d:(src_slots[0] + 1) * d].clone()
        for i in src_slots[1:]:
            b = b + s[:, i * d:(i + 1) * d]
        blocks.append(b)
    if hid:
        blocks.append(s[:, D_src:D_src + hid].clone())
    return th.cat(blocks, 1)


def keep_index(groups, d, D_src, hid):
    """Column index of the parent's first layer that each narrowed column was copied from (no fold)."""
    idx = [i * d + c for _, src_slots in groups for i in src_slots[:1] for c in range(d)]
    idx += list(range(D_src, D_src + hid))
    return th.tensor(idx, dtype=th.long)


def narrow(src, recurrent, k_dst, fold=False, seed=0):
    K_src, d = kd_for(src)
    D_src, D = K_src * d, k_dst * d
    groups, dropped = plan(K_src, k_dst, fold)
    hid = int(src.policy.lstm_output_dim) if recurrent else 0
    if recurrent:
        lid = getattr(src.policy, "lstm_input_dim", None) or int(src.policy.lstm_actor.input_size)
        assert lid == d, f"source LSTM reads {lid} inputs, expected the newest frame ({d})"
    lo = src.observation_space.low[:D_src].reshape(K_src, d)
    hi = src.observation_space.high[:D_src].reshape(K_src, d)
    lo_n = np.concatenate([lo[g[0]] for _, g in groups]).astype(np.float32)
    hi_n = np.concatenate([hi[g[0]] for _, g in groups]).astype(np.float32)

    class SpaceEnv(gymnasium.Env):
        def __init__(self):
            self.observation_space = gymnasium.spaces.Box(lo_n, hi_n, (D,), np.float32)
            self.action_space = gymnasium.spaces.Discrete(int(src.action_space.n))

        def reset(self, *, seed=None, options=None):
            return np.zeros(D, np.float32), {}

        def step(self, action):
            return np.zeros(D, np.float32), 0.0, False, False, {}

    kw = dict(learning_rate=src.learning_rate, n_steps=src.n_steps, batch_size=src.batch_size,
              n_epochs=src.n_epochs, gamma=src.gamma, gae_lambda=src.gae_lambda,
              clip_range=src.clip_range(1.0), ent_coef=src.ent_coef, vf_coef=src.vf_coef,
              max_grad_norm=src.max_grad_norm, target_kl=src.target_kl,
              policy_kwargs=dict(src.policy_kwargs or {}), device="cpu", verbose=0)
    th.manual_seed(seed)
    if recurrent:
        from sb3_contrib import RecurrentPPO
        dst = RecurrentPPO(type(src.policy), SpaceEnv(), seed=seed, **kw)
    else:
        from stable_baselines3 import PPO
        dst = PPO("MlpPolicy", SpaceEnv(), seed=seed, **kw)

    sd_src, sd_dst = src.policy.state_dict(), dst.policy.state_dict()
    assert list(sd_src) == list(sd_dst), "parent and narrowed policies have different tensor lists"
    new, narrowed = {}, []
    for name, t in sd_dst.items():
        s = sd_src[name]
        if t.shape == s.shape:
            new[name] = s.clone()
        elif (name.startswith("mlp_extractor.") and name.endswith(".0.weight")
              and s.shape[1] == D_src + hid and t.shape[1] == D + hid):
            new[name] = narrow_cols(s, groups, d, D_src, hid)
            narrowed.append(name)
        else:
            raise SystemExit(f"shape mismatch {name}: dst {tuple(t.shape)} src {tuple(s.shape)}")
    assert len(narrowed) == 2, f"expected the policy and value first layers to narrow, got {narrowed}"
    dst.policy.load_state_dict(new)

    # optimizer: parent's state, first-layer moments sliced to the kept columns
    names_s = [n for n, _ in src.policy.named_parameters()]
    names_d = [n for n, _ in dst.policy.named_parameters()]
    assert names_s == names_d, "parameter order differs; cannot map the optimizer state"
    osd = src.policy.optimizer.state_dict()
    idx = keep_index(groups, d, D_src, hid)
    n_sliced = 0
    for pi, name in enumerate(names_s):
        st = osd["state"].get(pi)
        if st is None or name not in narrowed:
            continue
        for key in ("exp_avg", "exp_avg_sq"):
            if key in st:
                st[key] = st[key][:, idx].clone()
                n_sliced += 1
    dst.policy.optimizer.load_state_dict(osd)
    dst.num_timesteps = src.num_timesteps
    dst._n_updates = src._n_updates
    info = dict(K_src=K_src, d=d, D_src=D_src, D=D, hid=hid, groups=groups, dropped=dropped, narrowed=narrowed,
                n_sliced=n_sliced, src_offs=OFFSETS_BY_K[K_src], dst_offs=OFFSETS_BY_K[k_dst])
    return dst, info


def check_structure(src, dst, info):
    """Entries of the narrowed net that are not the parent's (no fold: 0 means a pure column selection)."""
    sd_s, sd_d = src.policy.state_dict(), dst.policy.state_dict()
    bad = 0
    for name, t in sd_d.items():
        s = sd_s[name]
        exp = narrow_cols(s, info["groups"], info["d"], info["D_src"], info["hid"]) if name in info["narrowed"] else s
        bad += int((t != exp).sum())
    return bad


def expand(x, info):
    """Narrowed input [n, k*d] -> the parent input the narrowed net is exactly equal to: kept blocks in place,
    folded blocks = a copy of their kept block, dropped (unfolded) blocks = 0."""
    d, n = info["d"], x.shape[0]
    xp = np.zeros((n, info["D_src"]), np.float32)
    for j, src_slots in info["groups"]:
        for i in src_slots:
            xp[:, i * d:(i + 1) * d] = x[:, j * d:(j + 1) * d]
    return xp


def check_equivalence(src, dst, recurrent, info, n=256, T=40, seed=1):
    g = np.random.default_rng(seed)
    sc = {}
    with th.no_grad():
        if not recurrent:
            x = g.uniform(-2, 2, (n, info["D"])).astype(np.float32)
            xp = expand(x, info)
            lp = src.policy.get_distribution(th.as_tensor(xp)).distribution.logits
            lw = dst.policy.get_distribution(th.as_tensor(x)).distribution.logits
            vp, vw = src.policy.predict_values(th.as_tensor(xp)), dst.policy.predict_values(th.as_tensor(x))
            sc["logit"], sc["value"] = float(lp.abs().max()), float(vp.abs().max())
            return float((lp - lw).abs().max()), float((vp - vw).abs().max()), sc
        from sb3_contrib.common.recurrent.type_aliases import RNNStates
        hs, nl = src.policy.lstm_actor.hidden_size, src.policy.lstm_actor.num_layers

        def zeros():
            return RNNStates((th.zeros(nl, n, hs), th.zeros(nl, n, hs)), (th.zeros(nl, n, hs), th.zeros(nl, n, hs)))
        sp, sw = zeros(), zeros()
        wl = wv = 0.0
        for t in range(T):
            x = g.uniform(-2, 2, (n, info["D"])).astype(np.float32)
            xp = expand(x, info)
            start = th.as_tensor(np.full(n, t == 0, np.float32))
            dp, _ = src.policy.get_distribution(th.as_tensor(xp), sp.pi, start)
            dw, _ = dst.policy.get_distribution(th.as_tensor(x), sw.pi, start)
            vp = src.policy.predict_values(th.as_tensor(xp), sp.vf, start)
            vw = dst.policy.predict_values(th.as_tensor(x), sw.vf, start)
            _, _, _, sp = src.policy.forward(th.as_tensor(xp), sp, start)
            _, _, _, sw = dst.policy.forward(th.as_tensor(x), sw, start)
            wl = max(wl, float((dp.distribution.logits - dw.distribution.logits).abs().max()))
            wv = max(wv, float((vp - vw).abs().max()))
            sc["logit"] = max(sc.get("logit", 0.0), float(dp.distribution.logits.abs().max()))
            sc["value"] = max(sc.get("value", 0.0), float(vp.abs().max()))
        return wl, wv, sc


def agreement(src, dst, recurrent, info, obs_path):
    """Top-action agreement of narrowed vs parent on REAL parent-width stacked obs (the narrowed net reads the kept
    blocks of the same frames), run recurrently over the recorded episode boundaries."""
    from surgery_zero_itememb import run_seq
    z = np.load(obs_path)
    obs, starts = z["obs"].astype(np.float32), z["start"].astype(bool)
    assert obs.shape[1] == info["D_src"], f"{obs_path}: obs width {obs.shape[1]}, parent reads {info['D_src']}"
    d = info["d"]
    x = np.concatenate([obs[:, src_slots[0] * d:(src_slots[0] + 1) * d] for _, src_slots in info["groups"]], 1)
    lp, vp = run_seq(src, obs, starts, recurrent)
    lc, vc = run_seq(dst, x, starts, recurrent)
    ap, ac = lp.argmax(1), lc.argmax(1)
    pp = th.softmax(th.as_tensor(lp), 1).numpy()
    pc = th.softmax(th.as_tensor(lc), 1).numpy()
    tv = 0.5 * np.abs(pp - pc).sum(1)
    kl = (pp * (np.log(pp + 1e-12) - np.log(pc + 1e-12))).sum(1)
    same_p = (pp * pc).sum(1) / (pp * pp).sum(1)       # P(both sample the same move) / P(parent vs itself)
    r = dict(n=len(obs), starts=int(starts.sum()), top_agree=float((ap == ac).mean()),
             tv=float(tv.mean()), tv_max=float(tv.max()), kl=float(kl.mean()),
             sampled_match_ratio=float(same_p.mean()), value_absdiff=float(np.abs(vp - vc).mean()))
    print(f"[fs] real obs ({r['n']} steps, {r['starts']} episode starts): top action agrees "
          f"{int((ap == ac).sum())}/{r['n']} = {r['top_agree']:.1%}; policy TV mean {r['tv']:.4f} (max {r['tv_max']:.3f}), "
          f"KL(parent||narrowed) mean {r['kl']:.4f}; sampled-move match vs parent-with-itself {r['sampled_match_ratio']:.1%}; "
          f"value |diff| mean {r['value_absdiff']:.4f}", flush=True)
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--fold", action="store_true")
    ap.add_argument("--obs", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if os.environ.get("PS2_STACK_OFFSETS", "").strip():
        raise SystemExit("PS2_STACK_OFFSETS is set: this surgery maps lags by obs_stack.OFFSETS_BY_K; unset it")
    if a.k not in OFFSETS_BY_K:
        raise SystemExit(f"no lag list for K={a.k} in obs_stack.OFFSETS_BY_K")
    src, rec = load_any(a.src)
    if a.check:
        sys.exit(0 if kd_for(src)[0] == a.k else 1)
    if not a.dst:
        raise SystemExit("usage: surgery_frame_stack.py IN.zip OUT.zip --k K")
    K_src = kd_for(src)[0]
    if K_src == a.k:
        raise SystemExit(f"{a.src} already reads K={a.k} frames; nothing to do")
    dst, info = narrow(src, rec, a.k, a.fold, a.seed)
    nbad = check_structure(src, dst, info)
    wl, wv, sc = check_equivalence(src, dst, rec, info)
    num_ok, rl, rv = gate(wl, wv, sc)
    ok = num_ok and nbad == 0
    folded = {info["src_offs"][g[0]]: [info["src_offs"][i] for i in g[1:]] for _, g in info["groups"] if len(g) > 1}
    print(f"[fs] {a.src} ({'SkipLSTM' if rec else 'MLP'}, K={info['K_src']} lags {info['src_offs']}, {info['d']}/frame, "
          f"{info['D_src']} inputs) -> {a.dst} (K={a.k} lags {info['dst_offs']}, {info['D']} inputs); kept src blocks "
          f"{[g[0] for _, g in info['groups']]}; dropped lags {[info['src_offs'][i] for i in info['dropped']]}"
          f"{'; folded ' + str(folded) if folded else ''}; narrowed {info['narrowed']}; Adam moments sliced: "
          f"{info['n_sliced']}", flush=True)
    print(f"[fs] structure: {nbad} non-matching entries; exact check (dropped blocks "
          f"{'= their fold target' if a.fold else '= 0'}, random inputs, recurrent): max |logit diff| {wl:.2e} "
          f"(rel {rl:.1e} of |{sc.get('logit', 0):.1f}|), max |value diff| {wv:.2e} (rel {rv:.1e} of "
          f"|{sc.get('value', 0):.1f}|), rel tol {REL_TOL:.0e} -> {'PASS' if ok else 'FAIL'}", flush=True)
    if a.obs:
        agreement(src, dst, rec, info, a.obs)
    if not ok:
        raise SystemExit(1)
    dst.save(a.dst.removesuffix(".zip"))
    print(f"[fs] wrote {a.dst}; num_timesteps={dst.num_timesteps} n_updates={dst._n_updates}", flush=True)
