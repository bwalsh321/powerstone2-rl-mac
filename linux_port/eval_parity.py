"""Gate 4 — 50-episode frozen deterministic eval vs the Windows band.

Runs a checkpoint on ONE savestate slot and compares win% / picks / forms
to the HANDOFF band for that slot (kit #2, README_MIGRATION2.md):

    slot 2 (desert lv3 true-FFA): win ~63-75%, picks/ep ~6.8-7.5, forms ~1.6
    (training-time band; frozen deterministic tends to read a few pts HIGH)

Usage (from linux_port/, venv active):
    SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. python eval_parity.py \
        --core <flycast dylib/so> --game "../Power Stone 2 (USA).chd" \
        --slot 2 --episodes 50
"""
import argparse
import os

import numpy as np
from stable_baselines3 import PPO

from powerstone_env_libretro import PowerStoneEnvLibretro

BAND = {2: dict(win=(63.0, 75.0), picks=(6.8, 7.5), forms=(1.4, 1.9))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--model", default="./powerstone_v6_ppo.zip",
                    help="checkpoint zip (default: the Leg G warm-start copy)")
    ap.add_argument("--states", default="./states")
    ap.add_argument("--slot", type=int, default=2)
    ap.add_argument("--episodes", type=int, default=50)
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
    print("\n================ GATE 4 PARITY ================")
    print(f"model={os.path.basename(args.model)}  slot={args.slot}  n={n}  "
          f"mode={'stochastic' if args.stochastic else 'deterministic'}  "
          f"distinct-episodes~{uniq}")
    print(f"win% : {win_pct:5.1f}   ({wins}W/{losses}L/{tos}T)")
    print(f"picks: {picks:5.2f} /ep")
    print(f"forms: {forms:5.2f} /ep")
    band = BAND.get(args.slot)
    if band:
        checks = [("win%", win_pct, band["win"]),
                  ("picks", picks, band["picks"]),
                  ("forms", forms, band["forms"])]
        ok = True
        for name, v, (lo, hi) in checks:
            inb = lo <= v <= hi
            # deterministic eval reads high vs training-time bands — above
            # the box is a PASS with a note, below is the red flag
            above = v > hi
            ok &= (inb or above)
            tag = "IN BAND" if inb else ("ABOVE band (ok: frozen eval reads high)"
                                          if above else "BELOW BAND <-- suspect the port")
            print(f"  {name:6s} {v:6.2f} vs [{lo}-{hi}]  {tag}")
        print("RESULT:", "PARITY PASS — obs semantics survived the port"
              if ok else "PARITY FAIL — check RAM offsets / button map / cadence")
    else:
        print(f"(no Windows band recorded for slot {args.slot} — numbers only)")
    env.close()


if __name__ == "__main__":
    main()
