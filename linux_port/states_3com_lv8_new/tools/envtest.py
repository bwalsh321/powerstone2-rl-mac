import os, sys, random, traceback
import numpy as np
from powerstone_env_libretro import PowerStoneEnvLibretro
slots = [int(x) for x in sys.argv[1].split(",")]; inst = int(sys.argv[2])
env = PowerStoneEnvLibretro(core_path=os.path.expanduser("~/cores/flycast_libretro.so"),
    game_path="../Power Stone 2 (USA).chd", states_dir="/tmp/claude-1000/stamp60/envstates",
    state_slots=slots, instance_id=inst, bridge_dir=f"/tmp/claude-1000/stamp60/bridge/i{inst}")
# context as it would be once registered: same as 50-59 (stage dim 2, lv8) -- instance-level override only
env.SLOT_META = {**env.SLOT_META, **{k: (2, 8) for k in range(60, 69)}}
random.seed(0)
for s in slots:
    env.STATE_SLOTS = [s]
    try:
        obs = env.reset()
        act = list(env._active_opp)
        n = 0; dones = 0; rs = []
        for _ in range(100):
            obs, r, done, info = env.step(env.action_space.sample()); n += 1; rs.append(r)
            if done:
                dones += 1; obs = env.reset()
        print(f"[envtest] slot{s} OK active_opp={act} n_opp={len(act)} steps={n} dones={dones} "
              f"obs_len={len(obs)} finite={bool(np.all(np.isfinite(obs)))} diffdim={obs[env.DIFF_DIM]:.3f} "
              f"h={[round(x) for x in env.prev['h']]} rsum={sum(rs):.2f}", flush=True)
    except Exception:
        print(f"[envtest] slot{s} ERROR"); traceback.print_exc()
os._exit(0)
