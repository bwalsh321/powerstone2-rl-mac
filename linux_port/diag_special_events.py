"""diag_special_events.py (Sep 28 2026, Astra review 3 finding 2): annotated learner damage events.
Runs N episodes of a policy in the FFA env (one emulator instance, no training impact) with
PS2_SPECIAL_EVENTS set, then summarizes: of the learner's damage events, how many had ANY other seat
in state 25/26 now or within W frames, at what distance, and whether the special term fired.
Usage: PS2_SPECIAL_EVENTS=/path/events.txt <league_env flags> PS2_OBS_V2=1 python diag_special_events.py MODEL INST EPISODES
"""
import os, sys, re, numpy as np, torch as th
from stable_baselines3 import PPO
from obs_stack import StackedEnv, kd_for
from ffa_selfplay_env import FFASelfPlayEnv
ev_path = os.environ["PS2_SPECIAL_EVENTS"]
model = sys.argv[1]; inst = int(sys.argv[2]); N = int(sys.argv[3])
core = os.environ.get("PS2_CORE") or os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
slots = [int(x) for x in os.environ.get("PS2_STATE_SLOTS", "30").split(",")]
env = FFASelfPlayEnv(core_path=core, game_path="../Power Stone 2 (USA).chd", states_dir="./states_mixed",
                     instance_id=inst, state_slots=slots, bridge_dir=os.path.abspath(f"./bridge_probe_{inst}"), pool_dir="./pool_league")
M = PPO.load(model.removesuffix(".zip"), device="cpu"); K, D = kd_for(M)
env = StackedEnv(env, K)
obs = env.reset(); eps = 0
with th.no_grad():
    while eps < N:
        act, _ = M.predict(obs, deterministic=False)
        obs, r, done, info = env.step(act)
        if done:
            eps += 1; obs = env.reset()
# ---- summary
rows = [l for l in open(ev_path) if l.startswith("frame=")]
def seats(l): return re.findall(r"m(\d):st=(\d+),since=(-?\d+),dist=(\d+),alive=(\d)", l)
n = len(rows); fired = sum("fired=1" in l for l in rows)
def any_within(l, win, rad):
    return any((int(st) in (25, 26) or 0 <= int(since) <= win) and int(dist) <= rad and al == "1" for _, st, since, dist, al in seats(l))
print(f"[diag] {N} episodes, {n} learner damage events, term fired on {fired} ({100*fired/max(1,n):.0f}%)")
for win in (0, 120, 200, 400):
    for rad in (700, 1200, 2000, 99999):
        c = sum(any_within(l, win, rad) for l in rows)
        print(f"[diag] caster in special within {win:>3} frames and {rad:>5} units: {c:>4} events ({100*c/max(1,n):.0f}%)")
# distance distribution of hits that had a recent special (<=120 f) at ANY distance
ds = []
for l in rows:
    for _, st, since, dist, al in seats(l):
        if (int(st) in (25, 26) or 0 <= int(since) <= 120) and al == "1":
            ds.append(int(dist)); break
if ds:
    ds = np.array(ds); print(f"[diag] distance to the recent caster at hit time (n={len(ds)}): median {np.median(ds):.0f}, p25 {np.percentile(ds,25):.0f}, p75 {np.percentile(ds,75):.0f}, max {ds.max()}")
since_all = [int(since) for l in rows for _, st, since, dist, al in seats(l) if int(since) >= 0 and al == "1"]
if since_all:
    sa = np.array(since_all); print(f"[diag] frames since the caster's special at hit time (all hits with any prior special, n={len(sa)}): median {np.median(sa):.0f}, p25 {np.percentile(sa,25):.0f}, p75 {np.percentile(sa,75):.0f}")
