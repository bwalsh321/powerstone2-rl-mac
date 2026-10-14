"""bench_netwidth.py -- what a wider network costs (Oct 14 2026, bigger-network option).

LEARNER: the trainer's own update path on the SAME batch for every model: a RolloutBuffer of NENVS columns x n_steps
filled by train_selfplay_async.fill_buffer_from_chunks from recorded real observations (fixed actions/rewards), then
ppo_train.train() with the live optimizer settings (lr 5e-5, batch 256, prox KL ref). To time the update independent
of where target_kl happens to stop on synthetic data, target_kl is disabled and n_epochs fixed (--epochs), so every
model takes exactly the same number of gradient steps; the result is seconds per gradient step. Models are run
interleaved (A B A B ...) so background load hits them alike. An update's wall time is grad_steps x s/step, and
grad_steps is what target_kl allows (live leg 177: mean 408 of 800).
ACTOR: per-step inference exactly as actor_main does it (one obs, LSTM state carried, torch 1 thread), and the pool
seat path (PolicyRunner.act -> model.predict).

    python bench_netwidth.py A.zip B.zip [...] --obs real_obs.npz [--threads 4] [--epochs 2] [--rounds 3]
"""
import argparse
import os
import time

import numpy as np
import torch as th


def make_chunks(obs, starts, n, T, H, seed=7):
    g = np.random.default_rng(seed)
    out = []
    for i in range(n):
        idx = (np.arange(T) + int(g.integers(len(obs)))) % len(obs)
        st = starts[idx].astype(np.float32).copy()
        st[0] = 1.0
        c = dict(actor=i, version=0, versions=np.zeros(T, np.int64), obs=obs[idx],
                 actions=g.integers(0, 63, T).astype(np.int64), rewards=g.normal(0, 0.3, T).astype(np.float32),
                 episode_starts=st, values=g.normal(0, 1, T).astype(np.float32),
                 log_probs=(np.log(1 / 63) + g.normal(0, 0.1, T)).astype(np.float32),
                 last_value=0.0, last_done=False)
        for k in ("h_pi", "c_pi", "h_vf", "c_vf"):
            c[k] = np.zeros((T, 1, H), np.float32)
        out.append(c)
    return out


def load_for_learner(path, n_envs):
    import gymnasium
    from stable_baselines3.common.vec_env import DummyVecEnv
    from recurrent_policy import load_model
    from train_selfplay_async import _SpaceOnlyEnv
    probe = load_model(path)
    osp, asp = probe.observation_space, probe.action_space
    del probe

    class SpaceEnv(_SpaceOnlyEnv, gymnasium.Env):
        pass
    m = load_model(path, env=DummyVecEnv([lambda: SpaceEnv(osp, asp) for _ in range(n_envs)]))
    from stable_baselines3.common.utils import ConstantSchedule
    m.learning_rate = 5e-5
    m.lr_schedule = ConstantSchedule(5e-5)
    m.batch_size = 256
    m.target_kl = None
    m.verbose = 0
    from stable_baselines3.common.logger import configure
    m.set_logger(configure(None, [""]))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zips", nargs="+")
    ap.add_argument("--obs", required=True)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--nenvs", type=int, default=10)
    ap.add_argument("--act-steps", type=int, default=2000)
    a = ap.parse_args()
    os.environ.setdefault("PS2_PPO_KL_REF", "prox")
    import ppo_train
    from recurrent_policy import load_model, net_widths, PolicyRunner
    from train_selfplay_async import fill_buffer_from_chunks
    z = np.load(a.obs)
    obs, starts = z["obs"].astype(np.float32), z["start"].astype(bool)

    # ---------------- actor inference (1 thread, as actor_main)
    th.set_num_threads(1)
    from sb3_contrib.common.recurrent.type_aliases import RNNStates
    act_res = {}
    for p in a.zips:
        pol = load_model(p).policy
        pol.set_training_mode(False)
        L, H = pol.lstm_actor.num_layers, pol.lstm_actor.hidden_size
        zz = lambda: th.zeros((L, 1, H))
        best = []
        for rep in range(3):
            st = RNNStates((zz(), zz()), (zz(), zz()))
            t0 = time.perf_counter()
            with th.no_grad():
                for t in range(a.act_steps):
                    _, _, _, st = pol(th.as_tensor(obs[t % len(obs)][None]), st,
                                      th.tensor([float(starts[t % len(obs)])], dtype=th.float32))
                    pol.predict_values(th.as_tensor(obs[t % len(obs)][None]), st.vf, th.tensor([0.0]))  # chunk tail cost, amortised upper bound
            best.append((time.perf_counter() - t0) / a.act_steps)
        m = load_model(p)
        r = PolicyRunner(m)
        t0 = time.perf_counter()
        for t in range(a.act_steps):
            if starts[t % len(obs)]:
                r.reset()
            r.act(obs[t % len(obs)], deterministic=False)
        seat = (time.perf_counter() - t0) / a.act_steps
        act_res[p] = (min(best), seat)
        n_par = sum(x.numel() for x in pol.parameters())
        print(f"[actor] {os.path.basename(p)} {net_widths(pol)} params={n_par:,}: learner-seat step "
              f"{1e3 * min(best):.3f} ms (policy fwd + value, 1 thread); pool-seat PolicyRunner.act "
              f"{1e3 * seat:.3f} ms", flush=True)

    # ---------------- learner update (live threads)
    th.set_num_threads(a.threads)
    models = {p: load_for_learner(p, a.nenvs) for p in a.zips}
    for p, m in models.items():
        H = m.policy.lstm_actor.hidden_size
        m.n_epochs = 1
        last_values, dones = fill_buffer_from_chunks(m.rollout_buffer, make_chunks(obs, starts, a.nenvs, m.n_steps, H))
        m.rollout_buffer.compute_returns_and_advantage(last_values=last_values, dones=dones)
        ppo_train.train(m, 0)                     # warm-up: prox deepcopy, allocator, threads
    res = {p: [] for p in a.zips}
    for rnd in range(a.rounds):
        for p, m in models.items():
            m.n_epochs = a.epochs
            th.manual_seed(rnd)
            np.random.seed(rnd)
            t0 = time.perf_counter()
            ppo_train.train(m, rnd + 1)
            res[p].append(time.perf_counter() - t0)
    steps = a.epochs * (a.nenvs * models[a.zips[0]].n_steps // 256)
    base = None
    for p in a.zips:
        per = np.median(res[p]) / steps
        base = base or per
        print(f"[learner] {os.path.basename(p)} {net_widths(models[p].policy)}: update with {steps} grad steps "
              f"(batch 256, {a.nenvs}x{models[p].n_steps}): {' '.join(f'{x:.1f}s' for x in res[p])} -> median "
              f"{1e3 * per:.1f} ms/grad step ({per / base:.2f}x the first); at the live mean of 408 grad steps/update: "
              f"{408 * per:.1f} s", flush=True)


if __name__ == "__main__":
    main()
