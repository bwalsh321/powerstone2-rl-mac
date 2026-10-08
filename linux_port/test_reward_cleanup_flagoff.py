"""test_reward_cleanup_flagoff.py -- the reward-cleanup bundle (Oct 7 2026: PS2_DMG_ATTRIB, PS2_GEM_EP_CAP; the
itememb0 surgery touches no env code) must be INERT with its flags unset.

Same harness as test_obs_v4_flagoff.py (its dump()/compare() are reused): the same seeded episodes run in the
PARENT tree (an export of the commit before the bundle) and in this tree, under the LIVE recipe -- every VAR=VAL on
the last line of league_env.txt (PS2_OBS_V4=1 ITEMEMB=keep, OBJ_GRID_N=208, BUTTON_TAP, zero-sum, special attrib, ...)
plus the mixed-mode exports -- with a 430-dim pool policy driving seats P1/P3:
  ffa   FFASelfPlayEnv: learner obs, reward, done of every step + every pool seat's view, on 4 states_mixed slots;
  base  PowerStoneEnvLibretro (the env whose gem clamp PS2_GEM_EP_CAP changes) on held-out slots 90/93.
Every array must be BIT-IDENTICAL. --flag-on adds a third run of this tree with PS2_DMG_ATTRIB=hitsrc
PS2_GEM_EP_CAP=9: its observations must still be bit-identical (the flags are reward-only), and the number of steps
whose reward changed is reported.

    python test_reward_cleanup_flagoff.py --old-tree /export/linux_port --pool POOL_DIR_WITH_430_ZIPS \\
        --mixed-states /abs/states_mixed --states /abs/states --league-env /abs/league_env.txt [--instance 80]
"""
import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

FFA_SLOTS = (55, 61, 33, 12)
BASE_SLOTS = (90, 93)
FLAGS_ON = {"PS2_DMG_ATTRIB": "hitsrc", "PS2_GEM_EP_CAP": "9"}
MIXED = {"PS2_ENV": "ffa", "PS2_OBS_V2": "1", "PS2_STATE_SLOT": "0", "PS2_POOL_SAMPLING": "uniform",
         "PS2_FFA_SEATS": "0,2"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--old-tree", default="")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--mixed-states", required=True)
    ap.add_argument("--states", required=True)
    ap.add_argument("--league-env", default="")
    ap.add_argument("--game", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                                    "Power Stone 2 (USA).chd")))
    ap.add_argument("--instance", type=int, default=80)
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp"))
    ap.add_argument("--flag-on", action="store_true")
    ap.add_argument("--par", type=int, default=2)
    a = ap.parse_args()
    if a.part:
        sys.path[0] = os.getcwd()         # the env code of the tree we run in (cwd)
        import test_obs_v4_flagoff as T
        T.FFA_SLOTS, T.BASE_SLOTS = FFA_SLOTS, BASE_SLOTS
        T.dump(a)
        sys.stdout.flush()
        os._exit(0)
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    from test_obs_v4_flagoff import compare
    live = {}
    if a.league_env:
        line = [l for l in open(a.league_env).read().splitlines() if l.strip()][-1]
        live = dict(kv.split("=", 1) for kv in line.split())
    common = ["--pool", a.pool, "--mixed-states", a.mixed_states, "--states", a.states, "--game", a.game,
              "--steps", str(a.steps)]
    runs = [("old", a.old_tree, {}), ("new", here, {})]
    if a.flag_on:
        runs.append(("on", here, FLAGS_ON))
    procs = []
    for i, (tag, tree, extra) in enumerate(runs):
        for part in ("ffa", "base"):
            env = dict(os.environ, **live, **MIXED, **extra)
            for k in FLAGS_ON:
                if k not in extra:
                    env.pop(k, None)
            env["PS2_STAGGER_FRAMES"] = env.get("PS2_STAGGER_FRAMES", "240")
            out = os.path.join(a.tmp, f"rcflag_{tag}_{part}.npz")
            inst = a.instance + 2 * i + (part == "base")
            cmd = [sys.executable, os.path.abspath(__file__), "--part", part, "--out", out,
                   "--instance", str(inst)] + common
            while len([p for p in procs if p[3].poll() is None]) >= a.par:
                time.sleep(1.0)
            procs.append((tag, part, out, subprocess.Popen(cmd, cwd=tree, env=env)))
    for _, _, _, p in procs:
        p.wait()
    ok_all = True
    for part in ("ffa", "base"):
        ref = os.path.join(a.tmp, f"rcflag_old_{part}.npz")
        ok, rows = compare(ref, os.path.join(a.tmp, f"rcflag_new_{part}.npz"), False)
        ok_all &= ok
        for k, s0, s1, same, diff in rows:
            print(f"[cmp] {part:4s} flags-off {k:10s} {s0}: {'BIT-IDENTICAL' if same else 'DIFFERENT max|d|=%.3g' % diff}",
                  flush=True)
        if a.flag_on:
            r, n = np.load(ref), np.load(os.path.join(a.tmp, f"rcflag_on_{part}.npz"))
            obs_same = all(r[k].tobytes() == n[k].tobytes() for k in r.files if not k.startswith("rew_"))
            nrew = sum(int(r[k].size) for k in r.files if k.startswith("rew_"))
            nchg = sum(int((r[k] != n[k]).sum()) for k in r.files if k.startswith("rew_"))
            dsum = {k: round(float(n[k].sum() - r[k].sum()), 3) for k in r.files if k.startswith("rew_")}
            print(f"[on ] {part:4s} flags-on obs/done/views {'BIT-IDENTICAL' if obs_same else 'DIFFERENT'}; "
                  f"rewards changed on {nchg}/{nrew} steps; per-slot reward-sum change {json.dumps(dsum)}", flush=True)
            ok_all &= obs_same
    print("reward-cleanup flag-off bit-identity:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
