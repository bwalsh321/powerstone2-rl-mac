"""surgery_zero_itememb.py -- one-shot "itememb0" surgery for an ALREADY-430-wide policy (Oct 7 2026, reward-cleanup
bundle, item 3).

obs[12..17] is the slot-hash "item embedding": it encodes an arena SLOT, not an item (re/items_ground/GROUND.md 0.4).
The live lineage was widened 160 -> 430 at leg 134 with PS2_OBS_V4_ITEMEMB=keep, so its first layers still read those
six inputs. This surgery zeroes every weight that reads them:
  * mlp_extractor.{policy,value}_net.0.weight: columns j*430 + 12..17 for every frame slot j of the K-frame stack
    (the trailing lstm_output columns of a SkipLSTM are untouched);
  * SkipLSTM: lstm_actor / lstm_critic weight_ih_l0 columns 12..17 (the LSTM reads the newest frame);
  * the Adam moments (exp_avg, exp_avg_sq) of exactly those entries, so the columns STAY exactly zero in training:
    with PS2_OBS_V4_ITEMEMB=zero the inputs are 0, the gradients there are exactly 0, and a zeroed moment never moves.
Everything else (biases, hidden layers, heads, recurrent weights, the rest of the optimizer state, num_timesteps,
hyperparameters) is the parent's, bit for bit. The surgered policy is the parent evaluated with obs[12..17] = 0, which
is what it sees once league_env.txt says PS2_OBS_V4_ITEMEMB=zero (the env writes 0 there).

    python surgery_zero_itememb.py IN.zip OUT.zip [--obs real_obs.npz]     # surgery + equivalence report
    python surgery_zero_itememb.py --check IN.zip                          # exit 0 iff already zeroed
    python surgery_zero_itememb.py --collect OUT.npz --warm IN.zip --steps N --instance I   # real obs (needs env)

Equivalence report (--obs, real stacked observations + episode starts, collected with --collect):
  (1) structure: every tensor equals the parent's except the zeroed entries (count printed);
  (2) ZEROED obs: surgered(x0) vs parent(x0) on the same real obs with obs[12:18] = 0 in every frame slot, run
      recurrently over the real episode boundaries: logits / values must match EXACTLY (max |diff| == 0);
  (3) UNZEROED obs: parent(x) vs surgered(x) -> how many greedy actions change (the behaviour change the surgery
      actually makes on today's frames; expected small).
Exit 1 if (1) or (2) fails. Wired into league_leg_async.sh as the league_surgery.txt kind "itememb0".
"""
import argparse
import os
import sys

import numpy as np
import torch as th

ITEM = (12, 18)
D = 430


def load_any(path):
    from surgery_widen_v4 import load_any as _l
    return _l(path)


def item_cols(policy):
    """{param name: LongTensor of input columns to zero} for every first-layer / LSTM-input weight."""
    sd = policy.state_dict()
    hid = int(getattr(policy, "lstm_output_dim", 0) or 0) if hasattr(policy, "lstm_actor") else 0
    out = {}
    for name, t in sd.items():
        if name.startswith("mlp_extractor.") and name.endswith(".0.weight"):
            n_obs = t.shape[1] - hid
            assert n_obs % D == 0, f"{name}: {n_obs} obs inputs is not K x {D} (not an obs-v4 policy)"
            K = n_obs // D
            out[name] = th.tensor([j * D + c for j in range(K) for c in range(*ITEM)], dtype=th.long)
        elif name.endswith("weight_ih_l0"):
            assert t.shape[1] == D, f"{name}: LSTM reads {t.shape[1]} inputs, expected the newest {D}-dim frame"
            out[name] = th.arange(*ITEM, dtype=th.long)
    assert any(n.startswith("mlp_extractor.") for n in out), "no first-layer weights found"
    return out


def is_zeroed(path):
    m, _ = load_any(path)
    sd = m.policy.state_dict()
    return all(bool((sd[n][:, c] == 0).all()) for n, c in item_cols(m.policy).items())


def zero(model):
    cols = item_cols(model.policy)
    params = dict(model.policy.named_parameters())
    n_w = n_m = 0
    with th.no_grad():
        for name, c in cols.items():
            p = params[name]
            n_w += int((p[:, c] != 0).sum())
            p[:, c] = 0.0
            st = model.policy.optimizer.state.get(p, {})
            for key in ("exp_avg", "exp_avg_sq"):
                if key in st and st[key].shape == p.shape:
                    n_m += int((st[key][:, c] != 0).sum())
                    st[key][:, c] = 0.0
    return cols, n_w, n_m


def structure_bad(parent, child, cols):
    """Entries that differ from the parent anywhere OUTSIDE the zeroed columns, plus nonzero entries inside them."""
    sp, sc = parent.policy.state_dict(), child.policy.state_dict()
    bad = 0
    for name, t in sc.items():
        exp = sp[name].clone()
        if name in cols:
            exp[:, cols[name]] = 0.0
        bad += int((t != exp).sum())
    return bad


def run_seq(model, obs, starts, recurrent):
    """Logits and values over a real sequence (recurrent: carries LSTM state, resets at episode starts)."""
    pol = model.policy
    pol.set_training_mode(False)
    x = th.as_tensor(obs)
    with th.no_grad():
        if not recurrent:
            return pol.get_distribution(x).distribution.logits.numpy(), pol.predict_values(x).numpy().ravel()
        from sb3_contrib.common.recurrent.type_aliases import RNNStates
        L, H = pol.lstm_actor.num_layers, pol.lstm_actor.hidden_size
        z = lambda: th.zeros((L, 1, H))
        st = RNNStates((z(), z()), (z(), z()))
        lg, vs = [], []
        for t in range(len(obs)):
            s = th.as_tensor(starts[t:t + 1].astype(np.float32))
            d, _ = pol.get_distribution(x[t:t + 1], st.pi, s)
            v = pol.predict_values(x[t:t + 1], st.vf, s)
            _, _, _, st = pol.forward(x[t:t + 1], st, s)
            lg.append(d.distribution.logits.numpy()[0]); vs.append(float(v.numpy().ravel()[0]))
        return np.stack(lg), np.array(vs)


def zero_obs(obs):
    o = obs.copy()
    K = o.shape[1] // D
    for j in range(K):
        o[:, j * D + ITEM[0]:j * D + ITEM[1]] = 0.0
    return o


def report(parent, child, rec, cols, obs_path):
    bad = structure_bad(parent, child, cols)
    print(f"[ie0] structure: {bad} entries differ from the parent outside the zeroed columns / nonzero inside them")
    ok = bad == 0
    if not obs_path:
        return ok
    z = np.load(obs_path)
    obs, starts = z["obs"].astype(np.float32), z["start"].astype(bool)
    x0 = zero_obs(obs)
    nz = int((obs[:, [j * D + c for j in range(obs.shape[1] // D) for c in range(*ITEM)]] != 0).any(1).sum())
    lp0, vp0 = run_seq(parent, x0, starts, rec)
    lc0, vc0 = run_seq(child, x0, starts, rec)
    dl, dv = float(np.abs(lp0 - lc0).max()), float(np.abs(vp0 - vc0).max())
    exact = dl == 0.0 and dv == 0.0
    print(f"[ie0] zeroed real obs ({len(obs)} steps, {int(starts.sum())} episode starts): surgered vs parent "
          f"max |logit diff| {dl:.3g}, max |value diff| {dv:.3g} -> {'EXACT' if exact else 'NOT EXACT'}")
    lp, vp = run_seq(parent, obs, starts, rec)
    lc, vc = run_seq(child, obs, starts, rec)
    ap, ac = lp.argmax(1), lc.argmax(1)
    pp = th.softmax(th.as_tensor(lp), 1).numpy(); pc = th.softmax(th.as_tensor(lc), 1).numpy()
    tv = 0.5 * np.abs(pp - pc).sum(1)
    kl = (pp * (np.log(pp + 1e-12) - np.log(pc + 1e-12))).sum(1)
    print(f"[ie0] unzeroed real obs ({nz}/{len(obs)} steps carry a nonzero obs[12:18]): greedy action changes "
          f"{int((ap != ac).sum())}/{len(obs)} = {(ap != ac).mean():.2%}; policy TV mean {tv.mean():.4f} "
          f"(max {tv.max():.3f}), KL(parent||surgered) mean {kl.mean():.5f}; value |diff| mean "
          f"{np.abs(vp - vc).mean():.4f} (max {np.abs(vp - vc).max():.3f})")
    return ok and exact


def collect(a):
    """Real stacked learner obs from the training env (FFASelfPlayEnv under the caller's league flags; obs[12:18] as
    the env writes them -- run it with PS2_OBS_V4_ITEMEMB=keep so the hash is present)."""
    import random
    th.set_num_threads(1)
    random.seed(a.seed); np.random.seed(a.seed); th.manual_seed(a.seed)
    from ffa_selfplay_env import FFASelfPlayEnv
    from obs_stack import StackedEnv, kd_for
    from recurrent_policy import load_model, PolicyRunner
    env = FFASelfPlayEnv(core_path=os.environ["PS2_CORE"], game_path=os.environ["PS2_GAME"],
                         states_dir=os.environ.get("PS2_STATES_DIR", "./states_mixed"), instance_id=a.instance,
                         state_slots=[int(s) for s in os.environ["PS2_STATE_SLOTS"].split(",")],
                         bridge_dir=os.path.abspath(f"bridge_i{a.instance}"), pool_dir=a.pool)
    model = load_model(a.warm)
    K, _ = kd_for(model)
    env.set_action_mode(int(model.action_space.n))
    senv = StackedEnv(env, K) if K > 1 else env
    runner = PolicyRunner(model)
    obs = senv.reset(); runner.reset()
    O, S = [], []
    start = True
    for _ in range(a.steps):
        O.append(np.asarray(obs, np.float32)); S.append(start)
        act = runner.act(obs, deterministic=False)
        obs, r, done, info = senv.step(int(act))
        start = bool(done)
        if done:
            obs = senv.reset(); runner.reset()
    np.savez_compressed(a.collect, obs=np.stack(O), start=np.array(S))
    print(f"[collect] {len(O)} steps, {sum(S)} episode starts -> {a.collect}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--obs", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--collect", default="")
    ap.add_argument("--warm", default="")
    ap.add_argument("--pool", default="./pool_league")
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--instance", type=int, default=80)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.collect:
        collect(a)
        sys.stdout.flush()
        os._exit(0)
    if a.check:
        sys.exit(0 if is_zeroed(a.src) else 1)
    parent, rec = load_any(a.src)
    child, _ = load_any(a.src)
    cols, n_w, n_m = zero(child)
    print(f"[ie0] {a.src} ({'SkipLSTM' if rec else 'MLP'}): zeroed obs[12:18] columns in {sorted(cols)}: "
          f"{n_w} nonzero weights -> 0, {n_m} nonzero Adam moment entries -> 0")
    ok = report(parent, child, rec, cols, a.obs)
    print(f"[ie0] -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        sys.exit(1)
    child.save(a.dst.removesuffix(".zip"))
    print(f"[ie0] wrote {a.dst}")
