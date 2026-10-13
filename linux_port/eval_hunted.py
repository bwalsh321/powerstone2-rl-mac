"""eval_hunted.py -- "hunted" grading mode (Oct 10 2026, docs/HUNTER_PROJECT.md step 2).

Grades a model on the human-seat mixed lineups (states_mixed slot30-43: P1/P3 HUMAN Falcon, P4 = one lv8 COM of the
14 characters) inside FFASelfPlayEnv, deterministic, round-robin over the slots, paired pre-roll (visit k of a slot
gets pre-roll k * 240 / visits, so two runs replay the same start points and compare round by round):

  hunted    --hunters 0,2  P1 and P3 are hunter_bot.py (only hunt the bot), P4 the lv8 COM
  baseline  --hunters ""   P1 and P3 are a FROZEN copy of a policy (--opp, e.g. the graded zip itself), P4 the COM
  (mixed)   --hunters 0    P1 hunter, P3 frozen --opp

Per episode it records the result, the bot's damage taken by source seat (the game's own hit-source pointer, see
ffa_selfplay_env._hit_attacker; 'x' = unattributed), who landed the KO, and transforms per seat; one JSON line per
episode goes to --out. `--merge f1 f2 ...` prints the summary of several shard files.

Shards: --visit-offset V makes this shard's episode e the visit V + e // len(slots) of its slot (3 shards of 280
rounds over 14 slots: offsets 0, 7, 14 with 98, 98, 84 episodes). Contract flags as the leg was trained/graded:
PS2_OBS_V2=1 PS2_OBS_V3=1 PS2_OBS_V4=1 PS2_OBS_V4_ITEMEMB=keep PS2_OBJ_GRID_N=208 PS2_BUTTON_TAP=1, the 4-port harness
on PYTHONPATH. Episode cap PS2_FFA_MAX_STEPS defaults to 6000 here (the grading cap; the FFA training cap is 2000).
"""
import argparse
import json
import os
import sys
import tempfile


def parse_slots(text):
    out = []
    for part in text.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            out += list(range(int(lo), int(hi) + 1))
        elif part.strip():
            out.append(int(part))
    return out


def summarize(rows, label=""):
    import math
    n = len(rows)
    if not n:
        print("no episodes"); return
    w = sum(r["result"] == "win" for r in rows)
    l = sum(r["result"] == "loss" for r in rows)
    p = w / n
    se = math.sqrt(p * (1 - p) / n)
    dmg_in = sum(r["dmg_in"] for r in rows) / n
    src = {}
    for r in rows:
        for k, v in r["dmg_src"].items():
            src[k] = src.get(k, 0.0) + v
    ko = {}
    for r in rows:
        if r["result"] != "win" and r.get("ko"):
            ko[r["ko"]] = ko.get(r["ko"], 0) + 1
    forms = {}
    for r in rows:
        for k, v in r["forms"].items():
            forms[k] = forms.get(k, 0) + v
    print(f"==== {label} n={n}  win% {100 * p:.1f} +- {100 * se:.1f} ({w}W/{l}L/{n - w - l}T)")
    print(f"  bot damage taken /ep (health fractions): {dmg_in:.3f}  by source: "
          + " ".join(f"{k}={v / n:.3f}" for k, v in sorted(src.items())))
    print(f"  KO'd by (losses): " + " ".join(f"{k}={v}" for k, v in sorted(ko.items()))
          + f"   hunters={rows[0].get('hunters')}")
    print(f"  transforms /ep: " + " ".join(f"{k}={v / n:.2f}" for k, v in sorted(forms.items())))
    print(f"  bot dmg_out /ep {sum(r['dmg_out'] for r in rows) / n:.3f}  picks/ep {sum(r['picks'] for r in rows) / n:.2f}"
          f"  bot forms/ep {sum(r['bot_forms'] for r in rows) / n:.2f}  len {sum(r['len'] for r in rows) / n:.0f}")
    per = {}
    for r in rows:
        d = per.setdefault(r["slot"], [0, 0]); d[0] += r["result"] == "win"; d[1] += 1
    print("  per-slot: " + " ".join(f"{s}={per[s][0]}/{per[s][1]}" for s in sorted(per)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", nargs="*", default=None)
    ap.add_argument("--label", default="")
    ap.add_argument("--core", default=os.environ.get("PS2_CORE", os.path.expanduser("~/cores/flycast_libretro.so")))
    ap.add_argument("--game", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                                    "Power Stone 2 (USA).chd")))
    ap.add_argument("--states", default="./states_mixed")
    ap.add_argument("--model", default="./powerstone_v6_leg159_league.zip")
    ap.add_argument("--opp", default=None, help="frozen policy for non-hunter policy seats (default: --model)")
    ap.add_argument("--hunters", default="0,2", help="policy seats driven by hunter_bot.py ('' = none)")
    ap.add_argument("--stochastic", action="store_true", help="Oct 12 2026: sample the bot's moves (the way it trains)")
    ap.add_argument("--slots", default="30-43")
    ap.add_argument("--episodes", type=int, default=280)
    ap.add_argument("--visit-offset", type=int, default=0)
    ap.add_argument("--visits-total", type=int, default=20, help="visits per slot across all shards (pre-roll grid)")
    ap.add_argument("--instance", type=int, default=90)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.merge is not None:
        rows = [json.loads(l) for f in a.merge for l in open(f) if l.strip()]
        summarize(rows, a.label)
        return 0

    os.environ["PS2_HUNTER_SEATS"] = a.hunters
    os.environ["PS2_HUNTER_STATS"] = "1"
    os.environ.setdefault("PS2_FFA_SEATS", "0,2")
    os.environ.setdefault("PS2_FFA_MAX_STEPS", "6000")
    os.environ.pop("PS2_HUNTER_P", None)
    for k in ("PS2_ZERO_SUM", "PS2_START_HEALTH", "PS2_DRILL_DIR", "PS2_DRILL_P"):
        os.environ.pop(k, None)                     # grading: no training-only arena levers
    import torch as th
    th.set_num_threads(1)
    from ffa_selfplay_env import FFASelfPlayEnv
    from recurrent_policy import load_model, PolicyRunner
    from obs_stack import stack_for, FrameStack       # Oct 13 2026: stack_for = kd_for + PS2_OBS_STACK check

    pool = tempfile.mkdtemp(prefix="hunted_pool_")
    os.symlink(os.path.abspath(a.opp or a.model), os.path.join(pool, "opp.zip"))
    slots = parse_slots(a.slots)
    env = FFASelfPlayEnv(core_path=a.core, game_path=a.game, states_dir=a.states, state_slots=slots,
                         instance_id=a.instance, bridge_dir=os.path.abspath(f"bridge_eval_{a.instance}"),
                         pool_dir=pool, opp_deterministic=True)
    model = load_model(a.model)
    runner = PolicyRunner(model)
    env.set_action_mode(int(model.action_space.n))
    k_, d_ = stack_for(model)
    fs = FrameStack(k_, d_) if k_ > 1 else None
    env._legacy_proj_main = env._legacy_proj = (d_ == 122)
    env._legacy_item_main = env._legacy_item = (d_ <= 160)
    assert d_ <= env.OBS_DIM
    stag = int(os.environ.get("PS2_STAGGER_FRAMES", "240"))
    fo = open(a.out, "a") if a.out else None
    rows = []
    for ep in range(a.episodes):
        slot = slots[ep % len(slots)]
        env.STATE_SLOTS = [slot]
        k = a.visit_offset + ep // len(slots)
        env._preroll_next = int(k * stag / a.visits_total) % stag
        obs = env.reset()[:d_]
        obs = fs.reset(obs) if fs else obs
        runner.reset()
        done, info = False, {}
        while not done:
            act = runner.act(obs, deterministic=not a.stochastic)
            obs, r, done, info = env.step(act)
            obs = obs[:d_]
            obs = fs.push(obs) if fs else obs
        e = env._ep
        hz = env._hunt or {}
        row = dict(slot=slot, visit=k, result=info.get("result", "timeout"), len=env.steps,
                   dmg_in=float(e["dmg_in"]), dmg_out=float(e["dmg_out"]), picks=int(e["picks"]),
                   bot_forms=int(e["forms"]), dmg_src={kk: round(v, 4) for kk, v in hz.get("dmg", {}).items()},
                   ko=hz.get("ko"), forms=hz.get("forms", {}),
                   hunters=sorted(f"P{v.player + 1}" for v in env._views.values() if v.hunter is not None))
        rows.append(row)
        if fo:
            fo.write(json.dumps(row) + "\n"); fo.flush()
    summarize(rows, a.label or f"{os.path.basename(a.model)} hunters={a.hunters or '-'}")
    sys.stdout.flush()
    os._exit(0)                                     # skip the core's teardown abort


if __name__ == "__main__":
    sys.exit(main())
