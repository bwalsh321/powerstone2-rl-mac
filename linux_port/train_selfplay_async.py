"""Asynchronous actor-learner self-play trainer (Sep 11 2026, M4 era).

WHY: with SubprocVecEnv every learner step waits for the slowest of N
emulators, and a worker in episode reset (~1.0 s: loadstate + intro pump)
stalls all the others. Measured on the M4 Pro: one instance alone does 53
env steps/s, ten independent instances ~390 aggregate, ten lockstep workers
120. This trainer removes the lockstep.

SHAPE (the OpenAI Five / IMPALA / Sample Factory shape, single machine for
now): N_ACTORS processes each own one SelfPlayEnv and a CPU copy of the
policy. Each actor steps at its own pace, resets without blocking anyone,
and ships fixed-length trajectory chunks (n_steps transitions) to the
learner. The learner takes the first N_ENVS chunks to arrive, lays them into
stable-baselines3's own RolloutBuffer as columns (one column = one env's
consecutive n_steps transitions, exactly what collect_rollouts produces),
runs the UNCHANGED PPO.train(), and broadcasts new weights.

What is identical to train_selfplay.py: the env (SelfPlayEnv, obs contract,
rewards, savestates, opponent pool + sampling), the PPO hyperparameters
stored in the warm-start zip, the rollout size (n_steps x N_ENVS per
update), GAE, the checkpoint / pool-snapshot cadence and naming, the
warm-start + PS2_FRESH clock semantics. Terminal handling mirrors
SubprocVecEnv: on done the env auto-resets and the terminal observation is
dropped; the env's own MAX_STEPS timeout is a plain done (no TimeLimit
bootstrap), same as before.

What differs: chunks may be up to one policy update stale when they enter
the buffer (an actor finishes a chunk started under version k while the
learner is already at k+1). PPO's clipped objective is designed for this
regime; the [learner] line logs the version lag of every update so it can
be audited. The learner also holds no emulator, so it exits cleanly
(os._exit after the final save; actors are SIGKILLed).

The actor<->learner seam is two calls (send chunk / receive weights) over
multiprocessing pipes and a queue. A network transport for actors on other
machines is a drop-in replacement of that seam, not a redesign.

Env knobs (same names as train_selfplay.py plus three):
  PS2_CORE PS2_GAME PS2_POOL PS2_WARM(required) PS2_FRESH PS2_OUT
  PS2_TOTAL_STEPS PS2_STAGGER
  PS2_NACTORS        actor processes (default PS2_NENVS or 10)
  PS2_NENVS          rollout-buffer columns per update (default = PS2_NACTORS)
  PS2_INSTANCE_BASE  first emulator instance id (bridge_i<id>, system/dolphin-<id>);
                     use e.g. 20 to run beside a live relay leg without sharing dirs
"""
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
CORE = os.environ.get("PS2_CORE", os.path.join(ROOT, "../cores/flycast_libretro.so"))
GAME = os.environ.get("PS2_GAME", os.path.join(ROOT, "../Power Stone 2 (USA).chd"))
STATES = os.environ.get("PS2_STATES_DIR", os.path.join(ROOT, "states"))   # Sep 15: mixed lineage uses ./states_mixed
POOL_DIR = os.environ.get("PS2_POOL", os.path.join(ROOT, "opponent_pool"))
MODEL_PATH = os.environ.get("PS2_WARM",
                            os.path.join(ROOT, "powerstone_v6_ppo") + ".zip"
                            ).removesuffix(".zip")
FRESH = os.environ.get("PS2_FRESH", "0") == "1"
N_ACTORS = int(os.environ.get("PS2_NACTORS", os.environ.get("PS2_NENVS", "10")))
N_ENVS = int(os.environ.get("PS2_NENVS", str(N_ACTORS)))
TOTAL_STEPS = int(os.environ.get("PS2_TOTAL_STEPS", "2000000"))
INSTANCE_BASE = int(os.environ.get("PS2_INSTANCE_BASE", "0"))
CKPT_DIR = os.environ.get("PS2_CKPT_DIR", os.path.join(ROOT, "checkpoints_sp"))
STAGGER = float(os.environ.get("PS2_STAGGER", "20"))
# Sep 12 (leg-23 validation finding): actors that pull weights only at chunk
# boundaries feed the learner data that is a flat one update stale, which
# trips SB3's target_kl early stop inside the first epoch (165/195 updates
# ran 1 epoch vs lockstep's ~1.6). PS2_PULL_EVERY=<steps> lets actors apply
# new weights mid-chunk every that many steps (0 = boundary only, the
# validated-but-stale behaviour). Each step records the policy version that
# acted, so PPO's ratios stay exact and the seam check still applies.
PULL_EVERY = int(os.environ.get("PS2_PULL_EVERY", "0"))
SNAPSHOT_EVERY = 500_000
CHECKPOINT_EVERY = 100_000
# Sep 20 (character randomization): PS2_STATE_SLOTS="0,1,2,..." samples a slot per episode
# (base env reset does random.choice over STATE_SLOTS); PS2_STATE_SLOT stays as the single-slot form.
STATE_SLOTS = ([int(x) for x in os.environ["PS2_STATE_SLOTS"].split(",") if x.strip()]
               if os.environ.get("PS2_STATE_SLOTS") else [int(os.environ.get("PS2_STATE_SLOT", "1"))])
# Sep 13: PS2_ENV=ffa -> ffa_selfplay_env.FFASelfPlayEnv (four-seat self-play FFA,
# obs v2); default = the 2-seat SelfPlayEnv the league has always used.
ENV_KIND = os.environ.get("PS2_ENV", "selfplay")
CUSTOM_OBJECTS = {"clip_range": 0.2, "lr_schedule": lambda _: 2.5e-4}  # placeholders, see train_selfplay.py
ACTOR_TIMEOUT_S = 900.0          # learner waits at most this long for a chunk


# ------------------------------------------------------------------ actor
def actor_main(actor_id, instance_id, chunk_len, weights_conn, chunk_q, cfg):
    import torch as th
    th.set_num_threads(1)
    time.sleep(actor_id * cfg["stagger"])          # Metal init race (Law 8)
    from stable_baselines3 import PPO
    if cfg["env_kind"] == "ffa":
        from ffa_selfplay_env import FFASelfPlayEnv as EnvCls
    else:
        from selfplay_env import SelfPlayEnv as EnvCls
    env = EnvCls(core_path=cfg["core"], game_path=cfg["game"],
                 states_dir=cfg["states"], instance_id=instance_id,
                 state_slots=cfg["state_slots"],
                 bridge_dir=os.path.join(ROOT, f"bridge_i{instance_id}"),
                 pool_dir=cfg["pool_dir"])
    if cfg.get("obs_stack", 1) > 1:                     # Sep 22: K-frame stacked learner input
        from obs_stack import StackedEnv
        env = StackedEnv(env, cfg["obs_stack"])
    policy = PPO.load(cfg["warm_zip"], device="cpu",
                      custom_objects=CUSTOM_OBJECTS).policy
    policy.set_training_mode(False)
    version = -1

    def pull_weights(block):
        nonlocal version
        if block:
            weights_conn.poll(None)
        while weights_conn.poll():
            version, state = weights_conn.recv()
            policy.load_state_dict(state)

    pull_weights(block=True)                       # learner sends v0 first
    print(f"[actor {actor_id}] up: instance {instance_id}, policy v{version}", flush=True)

    obs_dim = env.observation_space.shape[0]
    obs = np.asarray(env.reset(), dtype=np.float32)
    ep_start = True
    while True:
        T = chunk_len
        c_obs = np.zeros((T, obs_dim), dtype=np.float32)
        c_act = np.zeros(T, dtype=np.int64)
        c_rew = np.zeros(T, dtype=np.float32)
        c_start = np.zeros(T, dtype=np.float32)
        c_val = np.zeros(T, dtype=np.float32)
        c_logp = np.zeros(T, dtype=np.float32)
        c_ver = np.zeros(T, dtype=np.int64)
        chunk_version = version
        for t in range(T):
            if cfg["pull_every"] and t and t % cfg["pull_every"] == 0:
                pull_weights(block=False)      # mid-chunk refresh (opt-in)
            c_ver[t] = version
            with th.no_grad():
                a, v, lp = policy(th.as_tensor(obs[None]))
            a_int = int(a.item())
            c_obs[t] = obs
            c_act[t] = a_int
            c_start[t] = float(ep_start)
            c_val[t] = float(v.item())
            c_logp[t] = float(lp.item())
            obs2, r, done, _info = env.step(a_int)
            c_rew[t] = float(r)
            if done:                               # SubprocVecEnv semantics: auto-reset,
                obs2 = env.reset()                 # terminal obs dropped
            ep_start = bool(done)
            obs = np.asarray(obs2, dtype=np.float32)
        with th.no_grad():
            last_value = float(policy.predict_values(th.as_tensor(obs[None])).item())
        chunk_q.put(dict(actor=actor_id, version=chunk_version, versions=c_ver,
                         obs=c_obs, actions=c_act, rewards=c_rew,
                         episode_starts=c_start, values=c_val, log_probs=c_logp,
                         last_value=last_value, last_done=ep_start))
        pull_weights(block=False)                  # newest weights, if any


# ---------------------------------------------------------------- learner
class _SpaceOnlyEnv:
    """A gymnasium env with the model's spaces and no dynamics: gives PPO.load
    the n_envs it needs to size the RolloutBuffer. Never stepped."""
    metadata = {}
    render_mode = None
    spec = None

    def __init__(self, observation_space, action_space):
        self.observation_space = observation_space
        self.action_space = action_space

    def reset(self, *, seed=None, options=None):
        return np.zeros(self.observation_space.shape, dtype=self.observation_space.dtype), {}

    def step(self, action):
        raise RuntimeError("space-only env is never stepped")

    def close(self):
        pass


def fill_buffer_from_chunks(buf, chunks):
    """Lay N_ENVS actor chunks into an SB3 RolloutBuffer as columns. Returns
    (last_values tensor, dones array) for compute_returns_and_advantage."""
    import torch as th
    buf.reset()
    T, n = buf.buffer_size, buf.n_envs
    assert len(chunks) == n
    for i, c in enumerate(chunks):
        assert c["obs"].shape[0] == T, (c["obs"].shape, T)
        buf.observations[:, i] = c["obs"]
        buf.actions[:, i, 0] = c["actions"]
        buf.rewards[:, i] = c["rewards"]
        buf.episode_starts[:, i] = c["episode_starts"]
        buf.values[:, i] = c["values"]
        buf.log_probs[:, i] = c["log_probs"]
    buf.pos = T
    buf.full = True
    last_values = th.as_tensor([c["last_value"] for c in chunks], dtype=th.float32)
    dones = np.array([c["last_done"] for c in chunks], dtype=bool)
    return last_values, dones


def main():
    import multiprocessing as mp
    import torch as th
    import gymnasium
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    warm_zip = MODEL_PATH + ".zip"
    assert os.path.exists(warm_zip), f"PS2_WARM required for the async trainer: {warm_zip}"
    os.makedirs(POOL_DIR, exist_ok=True)
    ckpt_dir = CKPT_DIR
    os.makedirs(ckpt_dir, exist_ok=True)

    # 1) spaces from the zip, 2) space-only vec env with N_ENVS columns,
    # 3) real load against it so _setup_model sizes the buffer (n_steps x N_ENVS)
    probe = PPO.load(warm_zip, device="cpu", custom_objects=CUSTOM_OBJECTS)
    obs_space, act_space = probe.observation_space, probe.action_space
    del probe
    # Sep 22 (frame stacking): PS2_OBS_STACK=K must match the warm zip's input (122*K).
    OBS_STACK = int(os.environ.get("PS2_OBS_STACK", "1"))
    assert obs_space.shape[0] == 122 * OBS_STACK, (
        f"warm zip expects {obs_space.shape[0]} inputs but PS2_OBS_STACK={OBS_STACK} gives {122 * OBS_STACK}; "
        f"run surgery_stack.py or fix league_env.txt")
    if OBS_STACK > 1:
        print(f"[config] obs_stack={OBS_STACK} (learner sees the last {OBS_STACK} frames, oldest first)", flush=True)

    class SpaceEnv(_SpaceOnlyEnv, gymnasium.Env):
        pass
    dummy = DummyVecEnv([lambda: SpaceEnv(obs_space, act_space) for _ in range(N_ENVS)])
    model = PPO.load(warm_zip, env=dummy, device="cpu", custom_objects=CUSTOM_OBJECTS)
    model.verbose = 1            # SB3 prints "Early stopping ... max kl" notices + its table
    # Sep 16 (entropy trigger fired at leg 38): optional entropy-coefficient override.
    # Unset = the zip's stored value (0.01 for this lineage). Blake decides per leg.
    if os.environ.get("PS2_ENT_COEF"):
        model.ent_coef = float(os.environ["PS2_ENT_COEF"])
        print(f"[config] ent_coef override -> {model.ent_coef}", flush=True)
    # Sep 16 (Blake: "run it 3 different times with different changes"): optimizer
    # overrides for the target_kl sweep. Inert unless the env var is set; every
    # override is printed so the leg log carries it. batch_size must divide
    # n_steps*n_envs (20480): 64/128/256/512/1024 all do.
    if os.environ.get("PS2_BATCH_SIZE"):
        model.batch_size = int(os.environ["PS2_BATCH_SIZE"])
        print(f"[config] batch_size override -> {model.batch_size}", flush=True)
    if os.environ.get("PS2_LR"):
        from stable_baselines3.common.utils import ConstantSchedule
        model.learning_rate = float(os.environ["PS2_LR"])
        model.lr_schedule = ConstantSchedule(model.learning_rate)
        print(f"[config] learning_rate override -> {model.learning_rate}", flush=True)
    if os.environ.get("PS2_TARGET_KL"):
        model.target_kl = float(os.environ["PS2_TARGET_KL"])
        print(f"[config] target_kl override -> {model.target_kl}", flush=True)
    T = model.n_steps
    buf = model.rollout_buffer
    assert buf.buffer_size == T and buf.n_envs == N_ENVS, (buf.buffer_size, buf.n_envs)
    total_steps, _ = model._setup_learn(TOTAL_STEPS, callback=None,
                                        reset_num_timesteps=FRESH,
                                        tb_log_name="async")
    print("[config] "
          f"learning_rate={model.learning_rate} n_steps={T} batch_size={model.batch_size} "
          f"n_epochs={model.n_epochs} gamma={model.gamma} gae_lambda={model.gae_lambda} "
          f"ent_coef={model.ent_coef} clip_range={model.clip_range(1.0)} "
          f"net_arch={(model.policy_kwargs or {}).get('net_arch')} warm={MODEL_PATH} "
          f"pool={POOL_DIR} n_envs={N_ENVS} n_actors={N_ACTORS} total_steps={total_steps} "
          f"instance_base={INSTANCE_BASE} pull_every={PULL_EVERY} env={ENV_KIND} "
          f"state_slots={STATE_SLOTS} obs_v2={os.environ.get('PS2_OBS_V2', '0')} "
          f"pool_sampling={os.environ.get('PS2_POOL_SAMPLING', 'uniform')} "
          f"states={STATES} seats={os.environ.get('PS2_FFA_SEATS', '0,2,3')} mode=async", flush=True)

    # actors
    ctx = mp.get_context("spawn")
    chunk_q = ctx.Queue(maxsize=2 * N_ACTORS)
    cfg = dict(core=CORE, game=GAME, states=STATES, pool_dir=POOL_DIR, obs_stack=OBS_STACK,
               warm_zip=warm_zip, state_slots=STATE_SLOTS, stagger=STAGGER,
               pull_every=PULL_EVERY, env_kind=ENV_KIND)
    conns, procs = [], []
    for i in range(N_ACTORS):
        parent, child = ctx.Pipe()
        p = ctx.Process(target=actor_main, daemon=True,
                        args=(i, INSTANCE_BASE + i, T, child, chunk_q, cfg))
        p.start()
        conns.append(parent)
        procs.append(p)

    version = 0

    def broadcast():
        state = {k: v.detach().cpu().clone() for k, v in model.policy.state_dict().items()}
        for c in conns:
            c.send((version, state))

    broadcast()

    tag = os.path.basename(os.environ.get("PS2_OUT", "selfplay")).replace("powerstone_v6_", "") or "selfplay"
    next_ckpt = (model.num_timesteps // CHECKPOINT_EVERY + 1) * CHECKPOINT_EVERY
    next_snap = (model.num_timesteps // SNAPSHOT_EVERY + 1) * SNAPSHOT_EVERY
    t_first = None
    n_updates = 0
    steps_at_first = model.num_timesteps
    while model.num_timesteps < total_steps:
        chunks = []
        while len(chunks) < N_ENVS:
            try:
                chunks.append(chunk_q.get(timeout=ACTOR_TIMEOUT_S))
            except Exception:
                dead = [i for i, p in enumerate(procs) if not p.is_alive()]
                print(f"[learner] no chunk for {ACTOR_TIMEOUT_S:.0f}s; dead actors: {dead}", flush=True)
                if dead:
                    for p in procs:
                        p.kill()
                    print("[learner] ACTOR DIED — halting (mid-leg crash semantics)", flush=True)
                    os._exit(1)
        if t_first is None:
            t_first = time.time()
        last_values, dones = fill_buffer_from_chunks(buf, chunks)
        buf.compute_returns_and_advantage(last_values=last_values, dones=dones)
        # SEAM INTEGRITY CHECK: chunks collected under the CURRENT weights must
        # reproduce their recorded log_probs/values exactly when re-evaluated
        # here (same policy, same obs, same actions). Any alignment or
        # weight-sync bug shows up as a non-tiny difference.
        allver = np.concatenate([c["versions"] for c in chunks])
        mask = allver == version
        if mask.any():
            with th.no_grad():
                o = th.as_tensor(np.concatenate([c["obs"] for c in chunks])[mask])
                a = th.as_tensor(np.concatenate([c["actions"] for c in chunks])[mask])
                v_re, lp_re, _ = model.policy.evaluate_actions(o, a)
            lp_rec = np.concatenate([c["log_probs"] for c in chunks])[mask]
            v_rec = np.concatenate([c["values"] for c in chunks])[mask]
            check = (f"[check] update {n_updates + 1} lag0_steps={int(mask.sum())}/{mask.size} "
                     f"logp_maxdiff={np.abs(lp_re.numpy() - lp_rec).max():.2e} "
                     f"value_maxdiff={np.abs(v_re.numpy().flatten() - v_rec).max():.2e}")
            print(check, flush=True)
        step_lag = float((version - allver).mean())
        model.num_timesteps += T * N_ENVS
        model._update_current_progress_remaining(model.num_timesteps, total_steps)
        t_train = time.time()
        model.train()
        train_s = time.time() - t_train
        n_updates += 1
        version += 1
        broadcast()
        lags = [version - 1 - c["version"] for c in chunks]
        ep_starts = sum(int(c["episode_starts"].sum()) for c in chunks)
        if n_updates == 1:            # rate is measured from the end of update 1
            t_first, steps_at_first = time.time(), model.num_timesteps
        elapsed = time.time() - t_first
        rate = (model.num_timesteps - steps_at_first) / elapsed if n_updates > 1 and elapsed > 0 else float("nan")
        print(f"[learner] update {n_updates} steps={model.num_timesteps} "
              f"{rate:.1f} steps/s (since end of update 1) train={train_s:.1f}s "
              f"lag(min/mean/max)={min(lags)}/{np.mean(lags):.2f}/{max(lags)} step_lag={step_lag:.2f} "
              f"actors={sorted(c['actor'] for c in chunks)} ep_starts_in_batch={ep_starts} "
              f"mean_reward={float(np.mean([c['rewards'].mean() for c in chunks])):+.4f}",
              flush=True)
        # PPO learning statistics from SB3's own logger (same keys as the
        # lockstep trainer's verbose table) — the validation comparison data.
        nv = model.logger.name_to_value
        keys = ["train/approx_kl", "train/clip_fraction", "train/entropy_loss",
                "train/explained_variance", "train/value_loss",
                "train/policy_gradient_loss", "train/loss", "train/n_updates"]
        print("[stats] update " + str(n_updates) + " " +
              " ".join(f"{k.split('/')[1]}={float(nv[k]):.4g}" for k in keys if k in nv),
              flush=True)
        model.logger.dump(step=model.num_timesteps)
        if model.num_timesteps >= next_ckpt:
            p = os.path.join(ckpt_dir, f"ps_sp_{model.num_timesteps}_steps")
            model.save(p)
            next_ckpt += CHECKPOINT_EVERY
        if model.num_timesteps >= next_snap:
            p = os.path.join(POOL_DIR, f"{tag}_{model.num_timesteps}_steps.zip")
            model.save(p)
            print(f"[pool] snapshot -> {p}", flush=True)
            next_snap += SNAPSHOT_EVERY

    out = os.environ.get("PS2_OUT") or (MODEL_PATH + ("_spleg" if FRESH else "_selfplay_leg1"))
    model.save(out)
    print("leg complete ->", out + ".zip", flush=True)
    for p in procs:
        p.kill()
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
