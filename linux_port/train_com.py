"""vs-COM trainer -- the lv8 leg (Aug 29, "the BIL leg").

Rationale (Blake + BIL, Aug 28-29): the rig-era curriculum stalled at COM
lv5 -- too much of the stream was easy wins, so the gradient kept polishing
weak-battle behavior. This leg inverts it: hard battles ONLY, slot 3 =
desert true-FFA @ COM lv8 (max), warm-started from selfplay_leg1 (which
already carries the BC prior). Self-play 1v1 stays the other training
track; this is the COM-difficulty track.

Shape mirrors train_selfplay.py minus the pool machinery: plain
PowerStoneEnvLibretro (opponents are the game's COMs, not policies),
SubprocVecEnv spawn + init stagger (macOS Metal race), warm start
mandatory (a fresh net vs lv8 gets ~no signal and that's a DIFFERENT
experiment -- do it with fresh BC when kit #4 comes off the rig).

Env changes riding with this leg (powerstone_env_v6.py, Aug 29):
  SLOT_META[3] = (2, 8)              desert dim, lv8, DIFF_DIM reads 1.0
  LOSS_SCALE_BY_LEVEL[8] = 0.2       effective terminal loss -2
  gem neg floor 1.5 at lv>=8         dying stays the worst outcome

Command (venv active, from linux_port/):
  SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. \
  PS2_CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" \
  PS2_NENVS=6 python -u train_com.py
"""
import os

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

from powerstone_env_libretro import PowerStoneEnvLibretro

ROOT = os.path.dirname(os.path.abspath(__file__))
CORE = os.environ.get("PS2_CORE", os.path.join(ROOT, "../cores/flycast_libretro.so"))
GAME = os.environ.get("PS2_GAME", os.path.join(ROOT, "../Power Stone 2 (USA).chd"))
STATES = os.path.join(ROOT, "states")
# Aug 29: PS2_WARM selects the warm-start zip (default: the promoted
# powerstone_v6_ppo = selfplay_leg1). For the FRESH-lineage lv8 leg
# (leg 3, the true BIL experiment): PS2_WARM=./powerstone_v6_bc256.zip
# PS2_FRESH=1 — fresh timeline, fresh save/checkpoint names carrying
# the lineage so zips can never be confused on disk.
MODEL_PATH = os.environ.get("PS2_WARM",
                            os.path.join(ROOT, "powerstone_v6_ppo") + ".zip"
                            ).removesuffix(".zip")
FRESH = os.environ.get("PS2_FRESH", "0") == "1"
N_ENVS = int(os.environ.get("PS2_NENVS", "6"))
TOTAL_STEPS = int(os.environ.get("PS2_TOTAL_STEPS", "2000000"))  # Aug 29: 2M for the leg-3 comparison program (slope is readable by then; leg2 was flat after 1M); extend the winner by resuming
STATE_SLOTS = [3]        # desert true-FFA @ COM lv8 -- hard battles only


def make_env(i):
    def _f():
        import time as _t
        _t.sleep(i * 20.0)  # Aug 29: 6s stagger let the Metal-init race through 3x on leg-3A launch; 20s is cheap insurance   # macOS Metal pipeline race -- stagger inits
        return PowerStoneEnvLibretro(
            core_path=CORE, game_path=GAME, states_dir=STATES,
            instance_id=i, state_slots=STATE_SLOTS,
            bridge_dir=os.path.join(ROOT, f"bridge_i{i}"))
    return _f


def main():
    venv = VecMonitor(SubprocVecEnv([make_env(i) for i in range(N_ENVS)],
                                    start_method="spawn"))

    if not os.path.exists(MODEL_PATH + ".zip"):
        raise SystemExit("warm start required: powerstone_v6_ppo.zip missing")
    print(f"warm-starting from {MODEL_PATH}.zip (selfplay_leg1 weights)")
    model = PPO.load(MODEL_PATH, env=venv, device="cpu",
                     custom_objects={"clip_range": 0.2,
                                     "lr_schedule": lambda _: 2.5e-4})

    lineage = os.path.basename(MODEL_PATH)
    ckpt_dir = "checkpoints_lv8_fresh" if FRESH else "checkpoints_lv8"
    out = os.path.join(ROOT, lineage + "_lv8leg")
    callbacks = [
        CheckpointCallback(save_freq=max(100_000 // N_ENVS, 1),
                           save_path=os.path.join(ROOT, ckpt_dir),
                           name_prefix="ps_lv8_" + lineage[-6:]),
    ]
    model.learn(total_timesteps=TOTAL_STEPS, callback=callbacks,
                reset_num_timesteps=FRESH)
    model.save(out)
    print("leg complete ->", out + ".zip")


if __name__ == "__main__":
    main()
