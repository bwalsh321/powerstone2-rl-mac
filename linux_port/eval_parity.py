"""Deterministic N-episode evaluation of one checkpoint on one savestate slot.

Two uses:

  1. Battery receipts (no --ref): prints the summary and exits 0. This is
     how league_battery.sh measures every leg (slot 3 = lv8 FFA, slot 2 =
     lv3 FFA held-out benchmark).

  2. Gate 4 parity (--ref): compares against a MATCHED reference, i.e. the
     same checkpoint's numbers from the machine you are migrating from, and
     exits 1 on PARITY FAIL. Example (leg 12 final vs its Mac battery):

         python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 \
             --episodes 50 --model ./powerstone_v6_leg12_league.zip \
             --ref 44/50,10.60,3.20

     Rule: win% passes if a two-proportion z-test against the reference is
     not significant at p<0.05 (n=50 vs n=50 cannot resolve a few points,
     and should not pretend to); picks/ep and forms/ep pass within +-15%.
     Deterministic evals are still not bit-reproducible (random reset
     delay), so treat a marginal fail as "run it again", a large one as
     obs divergence (RAM offsets / button map / cadence).

The old fixed Windows-era band (63-75% wins, "above band = ok") was removed
Sep 10 2026: it would have passed a large regression as parity.
"""
import argparse
import math
import os
import sys

import numpy as np
from stable_baselines3 import PPO

from powerstone_env_libretro import PowerStoneEnvLibretro


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def two_prop_p(k1, n1, k2, n2):
    """Two-sided two-proportion z-test p-value (normal approximation)."""
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = abs(k1 / n1 - k2 / n2) / se
    return math.erfc(z / math.sqrt(2))


def parse_ref(text):
    """'44/50,10.60,3.20' -> (44, 50, 10.60, 3.20)"""
    try:
        w, picks, forms = text.split(",")
        k, n = w.split("/")
        return int(k), int(n), float(picks), float(forms)
    except ValueError:
        sys.exit(f"--ref must look like 44/50,10.60,3.20 (got {text!r})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--model", default="./powerstone_v6_ppo.zip",
                    help="checkpoint zip (default: the Leg G warm-start copy)")
    ap.add_argument("--states", default="./states")
    ap.add_argument("--slot", type=int, default=2)
    ap.add_argument("--episodes", type=int, default=50)
    ap.add_argument("--ref", default=None,
                    help="matched reference 'wins/n,picks,forms' from the "
                         "source machine's battery for THIS checkpoint and "
                         "slot; enables the Gate 4 pass/fail (exit 1 on fail)")
    ap.add_argument("--stochastic", action="store_true",
                    help="sample actions instead of argmax — matches how the "
                         "training-time Windows band was actually measured, "
                         "and breaks determinism-induced repeated episodes")
    args = ap.parse_args()

    env = PowerStoneEnvLibretro(
        core_path=args.core, game_path=args.game, states_dir=args.states,
        state_slots=[args.slot], bridge_dir=os.path.abspath("./bridge_eval"))
    model = PPO.load(args.model.removesuffix(".zip"), device="cpu")

    eps = []
    for ep in range(args.episodes):
        obs = env.reset()
        done, info = False, {}
        while not done:
            action, _ = model.predict(obs, deterministic=not args.stochastic)
            obs, r, done, info = env.step(action)
        eps.append(dict(env._ep, result=info.get("result", "timeout")))

    n = len(eps)
    wins = sum(e["result"] == "win" for e in eps)
    losses = sum(e["result"] == "loss" for e in eps)
    tos = n - wins - losses
    win_pct = 100.0 * wins / n
    picks = float(np.mean([e["picks"] for e in eps]))
    forms = float(np.mean([e["forms"] for e in eps]))

    uniq = len({(e["result"], e["picks"], e["forms"],
                 round(e["dmg_out"], 3)) for e in eps})
    lo, hi = wilson(wins, n)
    print("\n================ EVAL SUMMARY ================")
    print(f"model={os.path.basename(args.model)}  slot={args.slot}  n={n}  "
          f"mode={'stochastic' if args.stochastic else 'deterministic'}  "
          f"distinct-outcome-tuples~{uniq}")
    print(f"win% : {win_pct:5.1f}   ({wins}W/{losses}L/{tos}T)   "
          f"95% Wilson [{lo:.0f}-{hi:.0f}]")
    print(f"picks: {picks:5.2f} /ep")
    print(f"forms: {forms:5.2f} /ep")
    ok = True
    if args.ref:
        rk, rn, rpicks, rforms = parse_ref(args.ref)
        pval = two_prop_p(wins, n, rk, rn)
        rlo, rhi = wilson(rk, rn)
        print("\n================ GATE 4 PARITY vs matched reference ================")
        print(f"  win%   {win_pct:6.1f} vs ref {100*rk/rn:6.1f} "
              f"[{rlo:.0f}-{rhi:.0f}]  two-proportion p={pval:.3f}  "
              f"{'ok' if pval >= 0.05 else 'FAIL'}")
        ok &= pval >= 0.05
        for name, v, r in (("picks", picks, rpicks), ("forms", forms, rforms)):
            rel = abs(v - r) / r if r else 0.0
            tag = "ok" if rel <= 0.15 else "FAIL"
            print(f"  {name:6s} {v:6.2f} vs ref {r:6.2f}  ({100*rel:4.1f}% off, "
                  f"tolerance 15%)  {tag}")
            ok &= rel <= 0.15
        print("RESULT:", "PARITY PASS — obs semantics survived the port"
              if ok else "PARITY FAIL — check RAM offsets / button map / cadence")
    env.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
