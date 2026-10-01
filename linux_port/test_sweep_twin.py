# Run from linux_port/ with the trainer env (PS2_OBS_V2=1 + league_env.txt flags): python test_sweep_twin.py [steps]
"""Twin test: every StateLineSynth gets a twin from the ORIGINAL ps2_ram (frozen copy), attached at the
same moment on the same bridge; after every env step all caches + the composed line must match exactly."""
import os, sys, importlib.util
import numpy as np, torch as th
spec = importlib.util.spec_from_file_location("ps2_ram_ref", os.path.join(os.path.dirname(os.path.abspath(__file__)), "archive/ps2_ram_pre_sweepshare_oct1.py"))
REF = importlib.util.module_from_spec(spec); spec.loader.exec_module(REF)
import flycast_bridge
pairs = []
_orig_attach = flycast_bridge.FlycastBridge.attach_synth
def attach(self, synth):
    _orig_attach(self, synth)
    if type(synth).__module__ == "ps2_ram":
        twin = REF.StateLineSynth(self.ram, bot_player=synth.bot + 1)
        twin.frame, twin._scan_last = synth.frame, synth._scan_last
        _orig_attach(self, twin)
        pairs.append((synth, twin))
flycast_bridge.FlycastBridge.attach_synth = attach
from stable_baselines3 import PPO
from obs_stack import StackedEnv, kd_for
from ffa_selfplay_env import FFASelfPlayEnv
N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
slots = [int(x) for x in os.environ["PS2_STATE_SLOTS"].split(",")]
env = FFASelfPlayEnv(core_path=os.path.expanduser("~/cores/flycast_libretro.so"), game_path="../Power Stone 2 (USA).chd",
                     states_dir="./states_mixed", instance_id=13, state_slots=slots,
                     bridge_dir=os.path.abspath("./bridge_probe_13"), pool_dir="./pool_league")
M = PPO.load("powerstone_v6_leg103_league", device="cpu"); K, D = kd_for(M)
env = StackedEnv(env, K)
groups = {id(s._hist) for s, _ in pairs}
print(f"[twin] {len(pairs)} synths, {len(groups)} sweep groups", flush=True)
F = ("_stone_cache", "_chest_frag", "_proj_cache", "_proj_cache_cls", "_proj_cache_v2")
obs = env.reset(); bad = 0; eps = 0; nproj = 0
with th.no_grad():
    for n in range(N):
        act, _ = M.predict(obs, deterministic=False)
        obs, r, done, info = env.step(act)
        for s, t in pairs:
            for f in F:
                if getattr(s, f, None) != getattr(t, f, None):
                    bad += 1; print(f"MISMATCH step {n} bot {s.bot+1} {f}: {getattr(s,f,None)!r} vs {getattr(t,f,None)!r}"[:300])
            if s._compose(0) != t._compose(0):
                bad += 1; print(f"MISMATCH step {n} bot {s.bot+1} line")
            nproj += len(s._proj_cache)
        if bad > 20: break
        if done: eps += 1; obs = env.reset()
print(f"[twin] {n+1} steps, {eps} episodes, projectile entries compared {nproj}, mismatches {bad}")
print("PASS" if bad == 0 else "FAIL")
