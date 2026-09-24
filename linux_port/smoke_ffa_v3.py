"""smoke_ffa_v3.py — mixed-arena smoke under obs v3: builds FFASelfPlayEnv exactly like the trainer's
actor (v2 pool policies in P1/P3, COM P4, character-random slots), stacks K=7, runs N steps with the
widened policy. Passes if shapes are right, the v3 block is live, pool views ran, no exception."""
import os, sys, numpy as np, torch as th
from stable_baselines3 import PPO
from obs_stack import StackedEnv, kd_for
from ffa_selfplay_env import FFASelfPlayEnv
assert os.environ.get("PS2_OBS_V3") == "1" and os.environ.get("PS2_OBS_V2") == "1"
model = sys.argv[1]; inst = int(sys.argv[2]) if len(sys.argv) > 2 else 13; N = int(sys.argv[3]) if len(sys.argv) > 3 else 400
core = os.environ.get("PS2_CORE") or os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" if os.uname().sysname == "Darwin" else "~/cores/flycast_libretro.so")
slots = [int(x) for x in os.environ.get("PS2_STATE_SLOTS", "0").split(",")]
env = FFASelfPlayEnv(core_path=core, game_path="../Power Stone 2 (USA).chd", states_dir="./states_mixed",
                     instance_id=inst, state_slots=slots, bridge_dir=os.path.abspath(f"./bridge_probe_{inst}"), pool_dir="./pool_league")
M = PPO.load(model.removesuffix(".zip"), device="cpu"); K, D = kd_for(M)
env = StackedEnv(env, K)
obs = env.reset(); assert obs.shape == (K * 160,), obs.shape
live = 0; eps = 0; views = set()
with th.no_grad():
    for n in range(N):
        act, _ = M.predict(obs, deterministic=False)
        obs, r, done, info = env.step(act)
        if np.abs(obs[-38:]).sum() > 0: live += 1
        for k, v in getattr(env, "_views", {}).items():
            views.add((k, kd_for(v.model)))
        if done:
            eps += 1; obs = env.reset()
print(f"[smoke] {N} steps, {eps} episodes done, v3 block live on {live}/{N} steps, pool views {sorted(views)}, obs {obs.shape}")
print("PASS" if live > 0 and views else "FAIL")
