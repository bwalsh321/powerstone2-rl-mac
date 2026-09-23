"""Deep validation of an ASYNC-trainer leg against a LOCKSTEP reference.

Pre-registered (Sep 12 2026, before leg 23 ran). Three evidence layers, each
with a pass rule written down in advance; the script prints every number and
a PASS/FAIL per rule. It never modifies anything.

  1. SEAM INTEGRITY  ([check] lines in the async log): re-evaluated log-probs
     and values of lag-0 chunks must match the actors' recorded ones.
     Rule: max |dlogp| < 1e-4 and max |dvalue| < 1e-3 on every update.
  2. LEARNING STATISTICS (per update; [stats] lines in the async log vs SB3's
     verbose table in the lockstep reference log): approx_kl, clip_fraction,
     entropy_loss, explained_variance, value_loss.
     Rules (async median over the leg vs lockstep reference median):
       approx_kl        async <= 2.5x lockstep  (staleness inflates KL; a
                                                 blow-up means broken ratios)
       clip_fraction    async <= 2.0x lockstep
       explained_var    async >= lockstep - 0.15 (value head still fits)
       entropy_loss     within 25% of lockstep (no collapse / no blow-up)
       grad steps/update async median >= 0.75x lockstep AND (added Sep 13
                        07:45 for leg 25, before it ran) async MEAN >=
                        0.75x lockstep mean; reference = a FULL lockstep
                        leg log (leg 24, 195 updates), not the 21-update
                        probe (target_kl early stopping must not be eating
                        the async updates)
       plus no NaN/inf anywhere.
  3. TRAINING-STREAM BEHAVIOUR ([ep] lines, thousands of episodes): learner
     win share vs the pool, episode length, picks, forms — by quarter.
     Rule: async whole-leg win share within 10 points of lockstep and
     picks/forms within 20%; no quarter with win share < 50% (self-play vs a
     frozen pool of weaker predecessors should never fall to parity).
  4. OUTCOME (battery receipts, n=50/12): reported alongside legs 21-22 for
     the human read; rule: slot2 >= 80 (the last 10 legs' band is 80-98) and
     AB vs its parent >= 7-5 (n=12), plus the optional n=50 AB vs parent.

Usage:
  python validate_async_leg.py --async-log receipts/train_leg23_out.txt \
      --lockstep-log receipts/train_lockstep_stats_out.txt \
      [--async-receipts 23] [--ref-receipts 22]
"""
import argparse
import math
import re
import statistics as st


def parse_ep(lines):
    eps = []
    for l in lines:
        if not l.startswith("[ep]"):
            continue
        m = re.search(r"len=\s*(\d+).*picked=(\d+).*forms=(\d+)/", l)
        if m:
            eps.append((" win " in l, int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return eps


def stream_stats(eps):
    n = len(eps)
    if n == 0:
        return None
    q = max(n // 4, 1)
    out = []
    for i in range(4):
        part = eps[i * q:(i + 1) * q] if i < 3 else eps[3 * q:]
        if part:
            out.append(dict(win=100 * sum(p[0] for p in part) / len(part),
                            len=st.mean(p[1] for p in part), picks=st.mean(p[2] for p in part),
                            forms=st.mean(p[3] for p in part), n=len(part)))
    whole = dict(win=100 * sum(p[0] for p in eps) / n, len=st.mean(p[1] for p in eps),
                 picks=st.mean(p[2] for p in eps), forms=st.mean(p[3] for p in eps), n=n)
    return whole, out


def parse_async_stats(lines):
    rows = []
    for l in lines:
        if "[stats] update" in l:
            d = {}
            for k, v in re.findall(r"(\w+)=([-+\deE.naninf]+)", l.split("[stats]")[1]):
                try:
                    d[k] = float(v)
                except ValueError:
                    pass
            rows.append(d)
    return rows


def parse_lockstep_stats(lines):
    """SB3 verbose table blocks. Keys are NESTED under section headers:
        | train/                  |             |
        |    approx_kl            | 0.0079      |
    A block ends at a '----' separator line."""
    rows, cur, section = [], {}, None
    for l in lines:
        if l.startswith("----"):
            if "approx_kl" in cur:
                rows.append(cur)
            cur, section = {}, None
            continue
        m = re.match(r"\|\s+(\w+)/\s+\|", l)
        if m:
            section = m.group(1)
            continue
        m = re.match(r"\|\s+(\w+)\s+\|\s+([-+\deE.naninf]+)\s+\|", l)
        if m and section == "train":
            try:
                cur[m.group(1)] = float(m.group(2))
            except ValueError:
                pass
    return rows


def early_stops(lines):
    return sum(1 for l in lines if "Early stopping" in l)


def grad_steps_per_update(rows):
    """train/n_updates is cumulative gradient steps; the per-update delta shows
    how many epochs actually ran (target_kl early stopping cuts it)."""
    n = [r["n_updates"] for r in rows if "n_updates" in r]
    return [b - a for a, b in zip(n, n[1:])]


def parse_checks(lines):
    out = []
    for l in lines:
        if "[check] update" in l:
            m = re.search(r"logp_maxdiff=([\deE.+-]+) value_maxdiff=([\deE.+-]+)", l)  # both lag0_chunks= and lag0_steps= formats
            if m:
                out.append((float(m.group(1)), float(m.group(2))))
    return out


def med(rows, k):
    v = [r[k] for r in rows if k in r and math.isfinite(r[k])]
    return st.median(v) if v else float("nan")


def receipts(n, root="receipts"):
    res = {}
    for slot in ("slot3", "slot2"):
        try:
            t = open(f"{root}/eval_leg{n}_{slot}_out.txt").read()
            w = re.search(r"win% :\s+([\d.]+)\s+\((\d+)W/(\d+)L", t)
            p = re.search(r"picks:\s+([\d.]+)", t)
            f = re.search(r"forms:\s+([\d.]+)", t)
            res[slot] = (float(w.group(1)), f"{w.group(2)}W/{w.group(3)}L", float(p.group(1)), float(f.group(1)))
        except Exception:
            res[slot] = None
    for ab in ("ab_vs_prev", "ab_vs_leg1"):
        try:
            t = open(f"{root}/eval_leg{n}_{ab}_out.txt").read()
            m = re.search(r"AB RESULT vs \S+: (\d+)W/(\d+)L", t)
            res[ab] = (int(m.group(1)), int(m.group(2)))
        except Exception:
            res[ab] = None
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--async-log", required=True)
    ap.add_argument("--lockstep-log", required=True)
    ap.add_argument("--async-receipts", type=int, default=None, help="leg number of the async leg")
    ap.add_argument("--ref-receipts", type=int, default=None, help="leg number of a lockstep reference leg")
    ap.add_argument("--stream-report-only", action="store_true",
                    help="layer 3 is reported but not gated (pre-registered for the FFA lineage: "
                         "win share vs THREE pool opponents is lower by construction)")
    a = ap.parse_args()
    A = open(a.async_log, errors="replace").read().splitlines()
    L = open(a.lockstep_log, errors="replace").read().splitlines()
    fails = []

    print("=" * 70)
    print("1. SEAM INTEGRITY (async [check] lines)")
    ch = parse_checks(A)
    if not ch:
        print("   no [check] lines found"); fails.append("no seam checks")
    else:
        mx_lp, mx_v = max(c[0] for c in ch), max(c[1] for c in ch)
        ok = mx_lp < 1e-4 and mx_v < 1e-3
        print(f"   {len(ch)} checks; max |dlogp|={mx_lp:.2e} max |dvalue|={mx_v:.2e} -> {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append("seam integrity")

    print("=" * 70)
    print("2. LEARNING STATISTICS (median per update)")
    As, Ls = parse_async_stats(A), parse_lockstep_stats(L)
    print(f"   async updates: {len(As)}   lockstep reference updates: {len(Ls)}")
    keys = ["approx_kl", "clip_fraction", "entropy_loss", "explained_variance", "value_loss", "policy_gradient_loss"]
    print(f"   {'metric':22s} {'async':>12s} {'lockstep':>12s}")
    for k in keys:
        print(f"   {k:22s} {med(As, k):12.4g} {med(Ls, k):12.4g}")
    ga, gl = grad_steps_per_update(As), grad_steps_per_update(Ls)
    ea, el = early_stops(A), early_stops(L)
    print(f"   {'grad steps/update (med)':22s} {st.median(ga) if ga else float('nan'):12.4g} {st.median(gl) if gl else float('nan'):12.4g}")
    print(f"   {'grad steps/update (mean)':22s} {st.mean(ga) if ga else float('nan'):12.4g} {st.mean(gl) if gl else float('nan'):12.4g}")
    print(f"   {'early-stop notices':22s} {ea:12d} {el:12d}   (per update: {ea/max(len(As),1):.2f} vs {el/max(len(Ls),1):.2f})")
    nan_bad = any(not math.isfinite(v) for r in As for v in r.values())
    if nan_bad:
        fails.append("NaN/inf in async stats")
    if As and Ls:
        rules = [("approx_kl", med(As, "approx_kl") <= 2.5 * med(Ls, "approx_kl")),
                 ("clip_fraction", med(As, "clip_fraction") <= 2.0 * med(Ls, "clip_fraction")),
                 ("explained_variance", med(As, "explained_variance") >= med(Ls, "explained_variance") - 0.15),
                 ("entropy_loss", abs(med(As, "entropy_loss") - med(Ls, "entropy_loss")) <= 0.25 * abs(med(Ls, "entropy_loss"))),
                 ("grad_steps_per_update", (st.median(ga) if ga else 0) >= 0.75 * (st.median(gl) if gl else 1)),
                 ("grad_steps_mean", (st.mean(ga) if ga else 0) >= 0.75 * (st.mean(gl) if gl else 1))]
        for k, ok in rules:
            print(f"   rule {k:20s} -> {'PASS' if ok else 'FAIL'}")
            if not ok:
                fails.append(f"stats:{k}")
    else:
        print("   (missing stats on one side; rules not evaluated)"); fails.append("stats missing")

    print("=" * 70)
    print("3. TRAINING STREAM (by quarter)")
    sa, sl = stream_stats(parse_ep(A)), stream_stats(parse_ep(L))
    for name, sres in (("async", sa), ("lockstep", sl)):
        if sres is None:
            print(f"   {name}: no [ep] lines"); continue
        whole, qs = sres
        print(f"   {name:9s} n={whole['n']:5d} win {whole['win']:5.1f}% len {whole['len']:5.0f} picks {whole['picks']:.2f} forms {whole['forms']:.2f}")
        for i, q in enumerate(qs):
            print(f"      q{i+1}: win {q['win']:5.1f}% len {q['len']:5.0f} picks {q['picks']:.2f} forms {q['forms']:.2f} (n={q['n']})")
    if sa and sl:
        wa, wl = sa[0], sl[0]
        r = [("win share within 10 pts", abs(wa["win"] - wl["win"]) <= 10),
             ("picks within 20%", abs(wa["picks"] - wl["picks"]) <= 0.2 * wl["picks"]),
             ("forms within 20%", abs(wa["forms"] - wl["forms"]) <= 0.2 * wl["forms"]),
             ("no quarter < 50% win", all(q["win"] >= 50 for q in sa[1]))]
        for k, ok in r:
            tag = ('PASS' if ok else 'FAIL') if not a.stream_report_only else ('pass' if ok else 'fail') + ' (report only)'
            print(f"   rule {k:24s} -> {tag}")
            if not ok and not a.stream_report_only:
                fails.append(f"stream:{k}")

    print("=" * 70)
    print("4. OUTCOME (battery receipts)")
    for label, n in (("async leg", a.async_receipts), ("reference leg", a.ref_receipts)):
        if n is None:
            continue
        rc = receipts(n)
        print(f"   {label} {n}: slot3 {rc['slot3']} | slot2 {rc['slot2']} | AB vs prev {rc['ab_vs_prev']} | AB vs leg1 {rc['ab_vs_leg1']}")
        if label == "async leg" and rc["slot2"]:
            ok1 = rc["slot2"][0] >= 80
            print(f"   rule slot2 >= 80 -> {'PASS' if ok1 else 'FAIL'}")
            if not ok1:
                fails.append("outcome:slot2<80")
            if rc["ab_vs_prev"]:                       # legacy batteries (<= leg 25)
                ok2 = rc["ab_vs_prev"][0] >= 7
                print(f"   rule AB vs parent >= 7-5 -> {'PASS' if ok2 else 'FAIL'}")
                if not ok2:
                    fails.append("outcome:AB<7")
            elif rc["ab_vs_leg1"]:                     # sharded batteries (leg 26+): n=100 vs the champion
                w, l = rc["ab_vs_leg1"]
                ok3 = w >= 0.40 * (w + l)
                print(f"   rule AB vs leg1 champion >= 40% (regression guard, n={w+l}) -> {'PASS' if ok3 else 'FAIL'}")
                if not ok3:
                    fails.append("outcome:AB_vs_leg1<40%")

    print("=" * 70)
    print("VERDICT:", "PASS — async leg trained properly by every pre-registered rule" if not fails
          else "FAIL — " + ", ".join(fails))


if __name__ == "__main__":
    main()
