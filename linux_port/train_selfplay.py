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
ELO-against-the-pool instead of raw win% (log_pool_winrate below), plus the
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
POOL_DIR = os.path.join(ROOT, "opponent_pool")  # seed by copying a few
                                                # checkpoints_v6 zips here
MODEL_PATH = os.path.join(ROOT, "powerstone_v6_ppo")   # warm start = Leg G
N_ENVS = int(os.environ.get("PS2_NENVS", "6"))  # benchmark first; see README
TOTAL_STEPS = 4_000_000
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
        _t.sleep(i * 6.0)
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
            p = os.path.join(self.pool_dir,
                             f"selfplay_{self.num_timesteps}_steps.zip")
            self.model.save(p)
            for env_i in range(self.training_env.num_envs):
                # workers refresh their pool listing lazily on next reset
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
        # 3.11 (sb3 warns and stores the exception object). predict()
        # never touches them, but .learn() calls both — replace with the
        # same values the fresh path below uses.
        model = PPO.load(MODEL_PATH, env=venv, device="cpu",
                         custom_objects={"clip_range": 0.2,
                                         "lr_schedule": lambda _: 2.5e-4})
    else:
        print("fresh model, net_arch [256,256]")
        model = PPO("MlpPolicy", venv, device="cpu", verbose=1,
                    n_steps=512, batch_size=512, learning_rate=2.5e-4,
                    tensorboard_log=os.path.join(ROOT, "powerstone_logs"),
                    policy_kwargs=dict(net_arch=[256, 256]))

    callbacks = [
        CheckpointCallback(save_freq=max(100_000 // N_ENVS, 1),
                           save_path=os.path.join(ROOT, "checkpoints_sp"),
                           name_prefix="ps_sp"),
        SnapshotToPool(SNAPSHOT_EVERY, POOL_DIR),
    ]
    model.learn(total_timesteps=TOTAL_STEPS, callback=callbacks,
                reset_num_timesteps=False)
    model.save(MODEL_PATH + "_selfplay_leg1")


if __name__ == "__main__":
    main()
