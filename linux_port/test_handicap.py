"""test_handicap.py -- the adaptive handicap's pure parts (Oct 19 2026; handicap.py). No emulator.

  1. update rule: forced wins drive h down to MIN, forced losses back up to 1.0, a win share at TARGET holds h;
     every move is <= STEP.
  2. carry-over: missing folder / corrupt / out-of-range / stale files are tolerated; fresh files are pooled.
  3. controller simulation (synthetic win curve, ~330 counted episodes per actor per leg as in leg 204): the
     per-result rule settles near TARGET; the "sign of a 200-episode EMA, +-0.01 per episode" rule limit-cycles.
  4. league_leg_async.sh ARENA parsing, run IN ISOLATION (only the ARENA lines are extracted and run in a temp dir;
     the wrapper itself is never executed: its retry path pkills every trainer on the machine).
  5. eval isolation (static): only ffa_selfplay_env.py / handicap.py read PS2_HANDICAP*; eval_parity.py (and the grade
     scripts that call it) build the base env; the FFA-env tools that grade or play (eval_hunted, record_hunted,
     play_vs) drop PS2_HANDICAP before importing the env.

    python test_handicap.py          (exit 1 on any failure)
"""
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from handicap import Handicap, parse_slots, enabled   # noqa: E402

FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


def t_rule():
    print("[1] update rule")
    hc = Handicap(target=0.55, h_min=0.5, step=0.01)
    check(hc.h == 1.0 and abs(hc.ema - 0.55) < 1e-12, "starts at h=1.0, ema=target")
    prev, moves = hc.h, []
    for _ in range(200):
        hc.update(True)
        moves.append(prev - hc.h)
        prev = hc.h
    check(all(m >= 0 for m in moves) and abs(moves[0] - 0.0045) < 1e-12, f"forced wins: h only falls, first step "
                                                                         f"{moves[0]:.4f} (= 0.01 x 0.45)")
    check(hc.h == 0.5, f"forced wins: h clamps at MIN (h={hc.h})")
    check(hc.ema > 0.8, f"forced wins: ema rises toward 1 (ema={hc.ema:.3f} after 200)")
    for _ in range(200):
        hc.update(False)
    check(hc.h == 1.0, f"forced losses: h back to 1.0 and clamps (h={hc.h})")
    hc2 = Handicap(target=0.55, h_min=0.5, step=0.01)
    hc2.h = 0.8
    seq = [True] * 11 + [False] * 9          # exactly 55% wins
    for w in seq * 10:
        hc2.update(w)
    check(abs(hc2.h - 0.8) < 1e-9, f"win share = target: net move 0 over 200 episodes (h={hc2.h:.6f})")
    check(parse_slots("50-68") == set(range(50, 69)) and parse_slots("30,55,60-61") == {30, 55, 60, 61},
          "slot parsing")
    check(not enabled({}) and not enabled({"PS2_HANDICAP": "0"}) and enabled({"PS2_HANDICAP": "1"}), "PS2_HANDICAP switch")
    e = Handicap.from_env(environ={"PS2_HANDICAP": "1", "PS2_HANDICAP_STATE": ""})
    check(e.target == 0.55 and e.h_min == 0.5 and e.slots == set(range(50, 69)) and e.state_dir == "",
          "defaults: target 0.55, min 0.5, slots 50-68")
    check(e.applies(55) and not e.applies(30) and not e.applies(43) and not e.applies(90), "applies to 50-68 only")


def t_carry():
    print("[2] carry-over")
    d = tempfile.mkdtemp(prefix="hcap_state_")
    a = Handicap(state_dir=os.path.join(d, "missing"), tag="70")
    a.load()
    check(a.h == 1.0 and a.carried == 0, "missing folder -> h=1.0")
    open(os.path.join(d, "hcap_i1.json"), "w").write("{not json")
    open(os.path.join(d, "hcap_i2.json"), "w").write(json.dumps({"h": 7.0, "ema": 0.5}))
    open(os.path.join(d, "hcap_i3.json"), "w").write(json.dumps({"ema": 0.5}))
    b = Handicap(state_dir=d, tag="70")
    b.load()
    check(b.h == 1.0 and b.carried == 0, "only corrupt / out-of-range / incomplete files -> h=1.0, no crash")
    for tag, h, ema in (("20", 0.80, 0.60), ("21", 0.70, 0.50)):
        w = Handicap(state_dir=d, tag=tag)
        w.h, w.ema = h, ema
        w.save()
    stale = os.path.join(d, "hcap_i99.json")
    open(stale, "w").write(json.dumps({"h": 0.5, "ema": 0.9}))
    old = time.time() - 3 * 86400
    os.utime(stale, (old, old))
    c = Handicap(state_dir=d, tag="70")
    c.load()
    check(abs(c.h - 0.75) < 1e-9 and abs(c.ema - 0.55) < 1e-9 and c.carried == 2,
          f"pooled mean of the 2 fresh files, stale + bad ones skipped (h={c.h:.3f} ema={c.ema:.3f} n={c.carried})")
    c.update(True)
    got = json.load(open(os.path.join(d, "hcap_i70.json")))
    check(abs(got["h"] - c.h) < 1e-6 and got["n"] == 1 and not [f for f in os.listdir(d) if ".tmp" in f],
          "update() writes its own file atomically (no tmp left)")
    e = Handicap(state_dir="", tag="70")
    e.update(True)
    check(not os.path.exists(os.path.join(os.getcwd(), "hcap_i70.json")), "state_dir '' -> nothing written")
    f = Handicap(state_dir="/proc/definitely/not/writable", tag="70")
    f.update(True)
    check(f.n == 1, "unwritable folder: update still works (save swallowed)")


def p_win(h):
    """Synthetic learner: 68% at full health (leg 204's 3-CPU share), losing ~0.8 of win share per unit of h."""
    return min(0.98, max(0.02, 0.68 - 0.8 * (1.0 - h)))


def sim(rule, episodes, seed, step=0.01, window=200.0, target=0.55):
    rng = random.Random(seed)
    h, ema, wins, hs = 1.0, target, [], []
    for _ in range(episodes):
        w = 1.0 if rng.random() < p_win(h) else 0.0
        wins.append(w)
        ema += (w - ema) / window
        if rule == "per_result":
            h = min(1.0, max(0.5, h - step * (w - target)))
        else:                                            # sign of the EMA error, +-step per episode
            h = min(1.0, max(0.5, h - step * (1.0 if ema > target else -1.0)))
        hs.append(h)
    return hs, wins


def t_sim():
    print("[3] controller simulation (synthetic win curve; h* = 0.84 gives 55%)")
    for rule in ("per_result", "sign_ema"):
        rows = []
        for seed in range(20):
            hs, wins = sim(rule, 1650, seed)               # ~5 legs of one actor
            tail_h, tail_w = hs[330:], wins[330:]
            rows.append((sum(tail_w) / len(tail_w), min(tail_h), max(tail_h),
                         (sum((x - sum(tail_h) / len(tail_h)) ** 2 for x in tail_h) / len(tail_h)) ** 0.5))
        wr = sum(r[0] for r in rows) / len(rows)
        lo = sum(r[1] for r in rows) / len(rows)
        hi = sum(r[2] for r in rows) / len(rows)
        sd = sum(r[3] for r in rows) / len(rows)
        print(f"     {rule:10s} legs 2-5: win share {wr:.3f}  h range {lo:.2f}-{hi:.2f}  h sd {sd:.3f}")
        if rule == "per_result":
            check(abs(wr - 0.55) < 0.02 and sd < 0.06, "per-result rule settles at target with small wobble")
            pr = sd
        else:
            check(sd > 2 * pr and (hi - lo) > 0.3, "sign-of-EMA rule swings far wider (why it was not used)")
    hs, _ = sim("per_result", 330, 0)
    k = next((i for i, x in enumerate(hs) if x < 0.88), None)
    print(f"     per_result: h first below 0.88 after {k} episodes (one leg of one actor = ~330)")
    check(k is not None and k < 330, "per-result rule reaches the neighbourhood of h* within one leg")


def t_wrapper():
    print("[4] league_leg_async.sh ARENA parsing (extracted lines only)")
    src = open(os.path.join(HERE, "league_leg_async.sh")).read().splitlines()
    i0 = next(i for i, l in enumerate(src) if l.startswith('ARENA="$(tr'))
    i1 = next(i for i, l in enumerate(src) if l.startswith("for kv in $ARENA"))
    block = "\n".join(src[i0:i1 + 1])
    check("pkill" not in block and "python" not in block, "extracted block runs nothing but parsing")
    d = tempfile.mkdtemp(prefix="hcap_wrap_")
    open(os.path.join(d, "league_env.txt"), "w").write(
        "PS2_ZERO_SUM=1 PS2_START_HEALTH=0.5,1.0 PS2_HANDICAP=1 PS2_HANDICAP_TARGET=0.55 PS2_HANDICAP_MIN=0.5\n"
        "PS2_HANDICAP_SLOTS=50-68 PS2_HANDICAP_STEP=0.01 PS2_HANDICAP_EMA=200 "
        "PS2_HANDICAP_STATE=claude_bridge/handicap_state PS2_HANDICAPX=9\n")
    script = (f"cd {d}\n{block}\nfor v in PS2_ZERO_SUM PS2_START_HEALTH PS2_HANDICAP PS2_HANDICAP_TARGET PS2_HANDICAP_MIN "
              "PS2_HANDICAP_SLOTS PS2_HANDICAP_STEP PS2_HANDICAP_EMA PS2_HANDICAP_STATE PS2_HANDICAPX; do "
              "echo \"$v=${!v-UNSET}\"; done\n")
    env = dict(os.environ, PS2_HANDICAP_MIN="0.1", PS2_HANDICAP_TARGET="0.9")   # inherited values must be replaced
    out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True).stdout
    got = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
    want = {"PS2_ZERO_SUM": "1", "PS2_START_HEALTH": "0.5,1.0", "PS2_HANDICAP": "1", "PS2_HANDICAP_TARGET": "0.55",
            "PS2_HANDICAP_MIN": "0.5", "PS2_HANDICAP_SLOTS": "50-68", "PS2_HANDICAP_STEP": "0.01",
            "PS2_HANDICAP_EMA": "200", "PS2_HANDICAP_STATE": "claude_bridge/handicap_state", "PS2_HANDICAPX": "UNSET"}
    for k, v in want.items():
        check(got.get(k) == v, f"{k} -> {got.get(k)!r} (want {v!r})")
    log = open(os.path.join(d, "wrapper_league.log")).read() if os.path.exists(os.path.join(d, "wrapper_league.log")) else ""
    check("ignoring unknown arena flag PS2_HANDICAPX=9" in log, "unknown look-alike flag is ignored and logged")
    open(os.path.join(d, "league_env.txt"), "w").write("PS2_ZERO_SUM=1\n")
    env = dict(os.environ, PS2_HANDICAP="1", PS2_HANDICAP_SLOTS="30-43")
    out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True).stdout
    got = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
    check(got.get("PS2_HANDICAP") == "UNSET" and got.get("PS2_HANDICAP_SLOTS") == "UNSET",
          "flag absent from league_env.txt -> an inherited PS2_HANDICAP is unset (off)")


def t_evals():
    print("[5] eval isolation (static)")
    readers = []
    for f in sorted(os.listdir(HERE)):
        if f.endswith((".py", ".sh")) and not f.startswith("test_"):
            txt = open(os.path.join(HERE, f), errors="replace").read()
            if re.search(r"""\.get\(["']PS2_HANDICAP|\[["']PS2_HANDICAP|^\s*(import handicap|from handicap)""", txt,
                         re.M):
                readers.append(f)
    check(set(readers) <= {"ffa_selfplay_env.py", "handicap.py"}, f"PS2_HANDICAP read only in {readers}")
    ep = open(os.path.join(HERE, "eval_parity.py")).read()
    check("FFASelfPlayEnv" not in ep and "PowerStoneEnvLibretro(" in ep, "eval_parity.py builds the base env")
    for g in ("stoch_grade.sh", "top_grade.sh", "league_battery.sh"):
        t = open(os.path.join(HERE, g)).read()
        check("eval_hunted" not in t or g == "league_battery.sh", f"{g}: grades through eval_parity.py")
    for f in ("eval_hunted.py", "record_hunted.py", "play_vs.py"):
        t = open(os.path.join(HERE, f)).read()
        i_pop = t.find('"PS2_HANDICAP"')
        i_imp = t.find("from ffa_selfplay_env import")
        check(0 <= i_pop < i_imp, f"{f}: drops PS2_HANDICAP before importing the FFA env")


if __name__ == "__main__":
    t_rule()
    t_carry()
    t_sim()
    t_wrapper()
    t_evals()
    print("handicap unit tests:", "PASS" if not FAILS else f"FAIL ({len(FAILS)})")
    sys.exit(1 if FAILS else 0)
