"""Sep 23 2026 (Astra review #1): every configured state slot must write the stage one-hot
and DIFF_DIM into the observation, for the learner seat and every opponent seat.
Runs the real _observe on a synthetic game state, no emulator. Exit 1 on failure."""
import os, sys
import numpy as np
os.environ.setdefault("PS2_OBS_V2", "1")
os.environ.setdefault("PS2_STATE_SLOTS", "0,10,11,12,13,14,15,16,17,18,19,20,21,22")
from powerstone_env_libretro import PowerStoneEnvLibretro as Env

SLOTS = [int(x) for x in os.environ["PS2_STATE_SLOTS"].split(",")]

def make_env(slot, agent_player):
    e = Env.__new__(Env)
    e.SLOT_META = dict(Env.SLOT_META)
    for s in SLOTS:                       # what FFASelfPlayEnv.__init__ does
        e.SLOT_META[s] = (1, 2)
    e.AGENT_PLAYER = agent_player
    e._active_opp = [j for j in range(4) if j != agent_player - 1]
    e._episode_slot = slot
    e.last_action = 0
    e._my_g_int = 0
    e._form_timer = 0
    e.baseline = [1000.0] * 4
    return e

def state():
    ps = [{"pos": (100.0 * j, 0.0, 50.0 * j), "face": (1.0, 0.0), "gems": 0,
           "form": 0, "meter": 0.0, "item": 0} for j in range(4)]
    return {"h": [1000.0] * 4, "players": ps, "stones": [], "stones_y": [],
            "proj": [], "chests": []}

fails = 0
for slot in SLOTS + [2, 3]:
    for seat in (1, 2, 3, 4):
        e = make_env(slot, seat)
        obs = e._observe(state(), state())
        stg = obs[e._STG0:e._STG0 + 4]
        exp_dim, exp_lv = e.SLOT_META[slot]
        want = np.zeros(4, dtype=np.float32); want[exp_dim] = 1.0
        ok = np.array_equal(stg, want) and abs(obs[e.DIFF_DIM] - exp_lv / 8.0) < 1e-6
        if not ok:
            fails += 1
            print(f"FAIL slot {slot} seat P{seat}: stage {stg.tolist()} diff {obs[e.DIFF_DIM]:.3f} "
                  f"(want dim {exp_dim}, diff {exp_lv/8:.3f})")
print(f"obs context: {len(SLOTS)+2} slots x 4 seats, {fails} failures, "
      f"OBS_CTX_FIX={Env.OBS_CTX_FIX}")
sys.exit(1 if fails else 0)
