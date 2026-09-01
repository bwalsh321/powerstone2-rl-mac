"""Mixed trainer — leg C of the leg-3 program (Aug 29).

4 workers vs the lv8 COM FFA (slot 3, plain env) + 2 workers 1v1
self-play (slot 1, SelfPlayEnv, pool from PS2_POOL). One PPO learner
sees both streams; the net can tell contexts apart via stage one-hot +
DIFF_DIM (slot3 declares 1.0, slot1 declares 0.25). The literature's
league-training compromise: hard fixed opponents for pressure, a
growing self opponent for adaptation.

Usage mirrors train_com.py:
  PS2_WARM=./powerstone_v6_bc256.zip PS2_FRESH=1 PS2_POOL=./pool_bc256 \
  SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PS2_CORE=<dylib> \
  PS2_NENVS=6 python -u train_mixed.py
"""
import os

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

from powerstone_env_libretro import PowerStoneEnvLibretro
from selfplay_env import SelfPlayEnv

ROOT = os.path.dirname(os.path.abspath(__file__))
CORE = os.environ.get("PS2_CORE", os.path.join(ROOT, "../cores/flycast_libretro.so"))
GAME = os.environ.get("PS2_GAME", os.path.join(ROOT, "../Power Stone 2 (USA).chd"))
STATES = os.path.join(ROOT, "states")
POOL_DIR = os.environ.get("PS2_POOL", os.path.join(ROOT, "opponent_pool"))
MODEL_PATH = os.environ.get("PS2_WARM",
                            os.path.join(ROOT, "powerstone_v6_ppo") + ".zip"
                            ).removesuffix(".zip")
FRESH = os.environ.get("PS2_FRESH", "0") == "1"
N_ENVS = int(os.environ.get("PS2_NENVS", "6"))
N_COM = int(os.environ.get("PS2_NCOM", "4"))   # workers 0..N_COM-1 = lv8 COM
TOTAL_STEPS = int(os.environ.get("PS2_TOTAL_STEPS", "2000000"))
SNAPSHOT_EVERY = 500_000


def make_env(i):
    def _f():
        import time as _t
        _t.sleep(i * 20.0)  # Aug 29: 6s stagger let the Metal-init race through 3x on leg-3A launch; 20s is cheap insurance   # macOS Metal pipeline race -- stagger inits
        if i < N_COM:
            return PowerStoneEnvLibretro(
                core_path=CORE, game_path=GAME, states_dir=STATES,
                instance_id=i, state_slots=[3],
                bridge_dir=os.path.join(ROOT, f"bridge_i{i}"))
        return SelfPlayEnv(
            core_path=CORE, game_path=GAME, states_dir=STATES,
            instance_id=i, state_slots=[1],
            bridge_dir=os.path.join(ROOT, f"bridge_i{i}"),
            pool_dir=POOL_DIR)
    return _f


class SnapshotToPool(BaseCallback):
    def __init__(self, every, pool_dir):
        super().__init__()
        self.every, self.pool_dir, self._last = every, pool_dir, 0

    def _on_step(self):
        if self.num_timesteps - self._last >= self.every:
            self._last = self.num_timesteps
            p = os.path.join(self.pool_dir,
                             f"selfplay_{self.num_timesteps}_steps.zip")
            self.model.save(p)
            print(f"[pool] snapshot -> {p}")
        return True


def main():
    os.makedirs(POOL_DIR, exist_ok=True)
    venv = VecMonitor(SubprocVecEnv([make_env(i) for i in range(N_ENVS)],
                                    start_method="spawn"))
    if not os.path.exists(MODEL_PATH + ".zip"):
        raise SystemExit("warm start required: " + MODEL_PATH + ".zip missing")
    print(f"warm-starting from {MODEL_PATH}.zip  (fresh timeline: {FRESH})")
    model = PPO.load(MODEL_PATH, env=venv, device="cpu",
                     custom_objects={"clip_range": 0.2,
                                     "lr_schedule": lambda _: 2.5e-4})
    lineage = os.path.basename(MODEL_PATH)
    callbacks = [
        CheckpointCallback(save_freq=max(100_000 // N_ENVS, 1),
                           save_path=os.path.join(ROOT, "checkpoints_mixed"),
                           name_prefix="ps_mx_" + lineage[-6:]),
        SnapshotToPool(SNAPSHOT_EVERY, POOL_DIR),
    ]
    model.learn(total_timesteps=TOTAL_STEPS, callback=callbacks,
                reset_num_timesteps=FRESH)
    out = MODEL_PATH + "_mixleg"
    model.save(out)
    print("leg complete ->", out + ".zip")


if __name__ == "__main__":
    main()
