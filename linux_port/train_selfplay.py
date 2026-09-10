"""Self-play trainer — Leg I candidate.

Shape mirrors train_v6_par.py (SubprocVecEnv + VecMonitor + checkpoints)
but with three deliberate changes, all motivated by the Leg H null result
and the fighting-game-AI survey (Phillip / slippi-ai / Blade & Soul):

 1. OPPONENT = frozen self, not COM. Pool seeded from checkpoints_v6 and
    grown with a snapshot every SNAPSHOT_EVERY steps. 50/50 recent/uniform
    sampling (see selfplay_env.OpponentPool).
 2. BIGGER NET: net_arch [256, 256] (SB3 default 2x64 was almost certainly
    under-capacity; Phillip used 2x128 for a simpler game). Only applies to
    a FRESH model — warm-starting Leg G keeps its 2x64 arch. Both paths are
    below; fresh + BC-style warm-up is the more principled restart, but
    warm-starting Leg G gets signal fastest. Start with warm start.
 3. BC REHEARSAL OFF by default. Rehearsal anchored the policy to demo
    level; self-play provides the curriculum now. Re-enable only if the
    policy collapses into degenerate play (spam one move), which is the
    failure mode rehearsal genuinely guards against.

Win/loss vs a frozen self is ~50% BY CONSTRUCTION at the start — track
ELO-against-the-pool instead of raw win% (NOT YET IMPLEMENTED), plus the
untouched ep_stats CSVs for behavior metrics (picks/forms/dmg).
"""
import os

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

from selfplay_env import SelfPlayEnv

ROOT = os.path.dirname(os.path.abspath(__file__))
CORE = os.environ.get("PS2_CORE", os.path.join(ROOT, "../cores/flycast_libretro.so"))
GAME = os.environ.get("PS2_GAME", os.path.join(ROOT, "../Power Stone 2 (USA).chd"))
STATES = os.path.join(ROOT, "states")          # slot<N>.state, VS-mode 2P
# Aug 29 (leg-3 program): PS2_POOL overrides the opponent pool dir (e.g.
# a dir seeded with ONLY the bc256 zip = "vs its prior self"); PS2_WARM
# overrides the warm-start zip; PS2_FRESH=1 starts the timestep clock at
# zero and names outputs by lineage.
POOL_DIR = os.environ.get("PS2_POOL", os.path.join(ROOT, "opponent_pool"))
MODEL_PATH = os.environ.get("PS2_WARM",
                            os.path.join(ROOT, "powerstone_v6_ppo") + ".zip"
                            ).removesuffix(".zip")
FRESH = os.environ.get("PS2_FRESH", "0") == "1"
N_ENVS = int(os.environ.get("PS2_NENVS", "6"))  # benchmark first; see README
TOTAL_STEPS = int(os.environ.get("PS2_TOTAL_STEPS", "2000000"))
SNAPSHOT_EVERY = 500_000
STATE_SLOTS = [1]        # start with ONE stage until parity is proven,
                          # then widen to the full lineup


def make_env(i):
    def _f():
        # Aug 28: stagger emulator init — two flycast instances building
        # Metal pipeline state simultaneously hit "failed assertion
        # renderPipelineState != nil" and kill the worker. A few seconds
        # of spacing at startup costs nothing over a multi-hour leg.
        import time as _t
        _t.sleep(i * float(os.environ.get("PS2_STAGGER", "20")))  # Aug 29: 6s let the Metal race through; Aug 31: env knob, leg4 uses 45
        return SelfPlayEnv(
            core_path=CORE, game_path=GAME, states_dir=STATES,
            instance_id=i, state_slots=STATE_SLOTS,
            bridge_dir=os.path.join(ROOT, f"bridge_i{i}"),
            pool_dir=POOL_DIR)
    return _f


class SnapshotToPool(BaseCallback):
    """Every SNAPSHOT_EVERY steps, drop the current model into the pool."""
    def __init__(self, every, pool_dir):
        super().__init__()
        self.every, self.pool_dir, self._last = every, pool_dir, 0

    def _on_step(self):
        if self.num_timesteps - self._last >= self.every:
            self._last = self.num_timesteps
            # Sep 2 review fix: tag snapshots by lineage/leg — PS2_FRESH
            # resets the step clock, so untagged names collided across legs
            # (leg N+1's 500k overwrote leg N's; Law 6 unappliable backward).
            _tag = os.path.basename(os.environ.get("PS2_OUT", "selfplay")
                                    ).replace("powerstone_v6_", "") or "selfplay"
            p = os.path.join(self.pool_dir,
                             f"{_tag}_{self.num_timesteps}_steps.zip")
            self.model.save(p)
            for env_i in range(self.training_env.num_envs):
                # Sep 9 audit: workers do NOT see this snapshot — the pool
                # file list is loaded once at env construction and reset()
                # samples that frozen list. Snapshots land on disk now and
                # become opponents at the NEXT leg's launch. (Frozen-per-leg
                # is methodologically clean; do not add live refresh without
                # changing the pre-registered recipe.)
                pass
            print(f"[pool] snapshot -> {p}")
        return True


def main():
    os.makedirs(POOL_DIR, exist_ok=True)
    # Aug 28: spawn, not fork/forkserver — macOS forked workers inherit
    # corrupted ObjC/Metal state (the NSXPCSharedListener "Connection
    # invalid" spam) and die in the GPU pipeline build. spawn gives each
    # worker a clean interpreter; costs a few seconds at startup only.
    venv = VecMonitor(SubprocVecEnv([make_env(i) for i in range(N_ENVS)],
                                    start_method="spawn"))

    if os.path.exists(MODEL_PATH + ".zip"):
        print(f"warm-starting from {MODEL_PATH}.zip (Leg G weights)")
        # Aug 24: the rig's zips carry clip_range/lr_schedule lambdas
        # pickled under the rig's python — they fail to deserialize under
        # 3.11 (sb3 warns and stores the exception object), so both are
        # replaced here so that load() does not choke.
        # Sep 10 (audit R6): the lr_schedule value below is a PLACEHOLDER,
        # not the training LR. SB3's load() calls _setup_model() afterwards,
        # which rebuilds lr_schedule from the saved `learning_rate` field.
        # Every warm-started league leg has therefore trained at the LR
        # stored in the zip (3e-4 for this lineage), not 2.5e-4. To change
        # the LR of a warm start, pass learning_rate in custom_objects. The
        # resolved values are printed below; trust that print, not comments.
        model = PPO.load(MODEL_PATH, env=venv, device="cpu",
                         custom_objects={"clip_range": 0.2,
                                         "lr_schedule": lambda _: 2.5e-4})
    else:
        print("fresh model, net_arch [256,256]")
        model = PPO("MlpPolicy", venv, device="cpu", verbose=1,
                    n_steps=512, batch_size=512, learning_rate=2.5e-4,
                    tensorboard_log=os.path.join(ROOT, "powerstone_logs"),
                    policy_kwargs=dict(net_arch=[256, 256]))

    # resolved configuration of the model that will actually train (audit
    # R6: comments and constructors drift; the loaded object is the truth)
    try:
        _cr = model.clip_range(1.0) if callable(model.clip_range) else model.clip_range
        print("[config] "
              f"learning_rate={getattr(model, 'learning_rate', '?')} "
              f"n_steps={getattr(model, 'n_steps', '?')} "
              f"batch_size={getattr(model, 'batch_size', '?')} "
              f"n_epochs={getattr(model, 'n_epochs', '?')} "
              f"gamma={getattr(model, 'gamma', '?')} "
              f"gae_lambda={getattr(model, 'gae_lambda', '?')} "
              f"ent_coef={getattr(model, 'ent_coef', '?')} clip_range={_cr} "
              f"net_arch={(getattr(model, 'policy_kwargs', None) or {}).get('net_arch')} "
              f"warm={MODEL_PATH if os.path.exists(MODEL_PATH + '.zip') else None} "
              f"pool={POOL_DIR} n_envs={N_ENVS} total_steps={TOTAL_STEPS}")
    except Exception as e:      # a log line must never kill a leg
        print(f"[config] could not print resolved config: {e!r}")

    callbacks = [
        CheckpointCallback(save_freq=max(100_000 // N_ENVS, 1),
                           save_path=os.path.join(ROOT, "checkpoints_sp"),
                           name_prefix="ps_sp"),
        SnapshotToPool(SNAPSHOT_EVERY, POOL_DIR),
    ]
    out = os.environ.get("PS2_OUT") or (MODEL_PATH + ("_spleg" if FRESH else "_selfplay_leg1"))
    model.learn(total_timesteps=TOTAL_STEPS, callback=callbacks,
                reset_num_timesteps=FRESH)
    model.save(out)
    print("leg complete ->", out + ".zip")


if __name__ == "__main__":
    main()
