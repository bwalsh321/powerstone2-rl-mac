#!/usr/bin/env python3
"""Merge sharded evaluation receipts into one receipt in the standard format.

The parallel battery (Sep 13 2026) runs each evaluation as K shards on K
emulator instances. Every shard is validated with the same rules as
check_receipt.py (summary header for the right model, W+L+T == episodes,
per-episode lines for A/B), then the shards are pooled: wins/losses/timeouts
summed, picks/forms averaged weighted by episodes, a fresh Wilson interval.
The merged file is what the relay, HANDOFF tooling and validate_async_leg.py
read, so it reproduces the single-run summary format exactly, plus a
"shards=" note.

    merge_receipts.py slot --model <zip> --slot N --per-shard E --out <file> <shard files...>
    merge_receipts.py ab   --model <zip> --opp <zip> --per-shard E --out <file> <shard files...>

Exit 0 = every shard complete and the merged receipt written. Exit 1 =
any shard invalid (reason on stderr; nothing written). Stdlib only.
"""
import argparse
import math
import os
import re
import sys


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def read(path):
    if not os.path.isfile(path):
        return None
    with open(path, errors="replace") as f:
        return f.read()


def slot_shard(path, model, slot, per_shard, slots=None):
    t = read(path)
    if t is None:
        return None, f"{path}: missing"
    m = re.search(r"model=(\S+)\s+slot=(\d+)\s+n=(\d+)", t)
    if not m:
        return None, f"{path}: no summary header"
    per_slot = {}
    if slots:                                            # Sep 25 (Astra): the receipt must name the set
        ms = re.search(r"slots=([0-9,]+)", t)
        if not ms or ms.group(1) != slots:
            return None, f"{path}: slots={ms.group(1) if ms else None}, expected {slots}"
        found = re.findall(r"slot(\d+)=(\d+)W/(\d+)", t)
        for s_, w_, n_ in found:
            per_slot[int(s_)] = (int(w_), int(n_))
        want = sorted(int(x) for x in slots.split(","))
        if len(found) != len(per_slot):
            return None, f"{path}: duplicate per-slot entries"
        if sorted(per_slot) != want:
            return None, f"{path}: per-slot counts missing for {slots}"
        # Sep 28 (Astra review 3, finding 4): the counts must be POSSIBLE and BALANCED
        each = per_shard // len(want)
        if each * len(want) != per_shard:
            return None, f"{path}: n={per_shard} not divisible across {len(want)} lineups"
        for s_, (w_, n_) in per_slot.items():
            if w_ < 0 or n_ < 0 or w_ > n_:
                return None, f"{path}: impossible per-slot count slot{s_}={w_}W/{n_}"
            if n_ != each:
                return None, f"{path}: unbalanced slot{s_}: {n_} episodes, expected {each}"
        if sum(n_ for _, n_ in per_slot.values()) != per_shard:
            return None, f"{path}: per-slot episodes sum to {sum(n_ for _, n_ in per_slot.values())}, expected {per_shard}"
    if m.group(1) != os.path.basename(model):
        return None, f"{path}: summary is for {m.group(1)}"
    if int(m.group(2)) != slot:
        return None, f"{path}: slot {m.group(2)}, expected {slot}"
    if int(m.group(3)) != per_shard:
        return None, f"{path}: n={m.group(3)}, expected {per_shard}"
    w = re.search(r"win%\s*:\s*[\d.]+\s*\((\d+)W/(\d+)L/(\d+)T\)", t)
    p = re.search(r"picks:\s*([\d.]+)", t)
    f = re.search(r"forms:\s*([\d.]+)", t)
    u = re.search(r"distinct-outcome-tuples~(\d+)", t)
    if not (w and p and f):
        return None, f"{path}: win/picks/forms lines missing"
    W, L, T = (int(x) for x in w.groups())
    if W + L + T != per_shard:
        return None, f"{path}: W+L+T={W+L+T}, expected {per_shard}"
    if per_slot and sum(w_ for w_, _ in per_slot.values()) != W:
        return None, f"{path}: per-slot wins sum to {sum(w_ for w_, _ in per_slot.values())}, expected {W}"
    return dict(W=W, L=L, T=T, picks=float(p.group(1)), forms=float(f.group(1)),
                uniq=int(u.group(1)) if u else 0, n=per_shard, per_slot=per_slot), None


def ab_shard(path, model, opp, per_shard):
    t = read(path)
    if t is None:
        return None, f"{path}: missing"
    m = re.search(r"AB RESULT vs (\S+):\s*(\d+)W/(\d+)L/(\d+)T", t)
    if not m:
        return None, f"{path}: no AB RESULT line"
    if m.group(1) != os.path.basename(opp):
        return None, f"{path}: AB vs {m.group(1)}, expected {os.path.basename(opp)}"
    W, L, T = (int(x) for x in m.groups()[1:])
    if W + L + T != per_shard:
        return None, f"{path}: W+L+T={W+L+T}, expected {per_shard}"
    lm = re.search(r"\[ab\]\s*model=(\S+)", t)
    if lm and lm.group(1) != os.path.basename(model):
        return None, f"{path}: probe loaded {lm.group(1)}"
    if len(re.findall(r"\[ab\] ep \d+/\d+:", t)) != per_shard:
        return None, f"{path}: per-episode line count != {per_shard}"
    return dict(W=W, L=L, T=T, n=per_shard), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["slot", "ab"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--opp")
    ap.add_argument("--slot", type=int)
    ap.add_argument("--slots", default=None, help="Sep 25: the exact held-out set every shard must declare (slots=...)")
    ap.add_argument("--per-shard", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("shards", nargs="+")
    a = ap.parse_args()
    parts, bad = [], []
    for sh in a.shards:
        r, err = (slot_shard(sh, a.model, a.slot, a.per_shard, a.slots) if a.kind == "slot"
                  else ab_shard(sh, a.model, a.opp, a.per_shard))
        if err:
            bad.append(err)
        else:
            parts.append(r)
    if bad:
        for b in bad:
            print(f"SHARD INVALID: {b}", file=sys.stderr)
        sys.exit(1)
    n = sum(p["n"] for p in parts)
    W, L, T = (sum(p[k] for p in parts) for k in ("W", "L", "T"))
    lo, hi = wilson(W, n)
    lines = []
    if a.kind == "slot":
        picks = sum(p["picks"] * p["n"] for p in parts) / n
        forms = sum(p["forms"] * p["n"] for p in parts) / n
        uniq = sum(p["uniq"] for p in parts)
        # Oct 7 2026 (audit): the per-shard tuple count never saw duplicates ACROSS shards (the leg 110/111 seed bug
        # replayed the same 50 rounds in every shard and still read ~950). Count globally distinct [ep] lines.
        _eps = set()
        for _sh in a.shards:
            try:
                _eps.update(l.strip() for l in open(_sh) if l.startswith("[ep]"))
            except OSError:
                pass
        lines += ["", "================ EVAL SUMMARY ================",
                  f"model={os.path.basename(a.model)}  slot={a.slot}  n={n}  mode=deterministic  "
                  f"distinct-outcome-tuples~{uniq}  distinct-episodes={len(_eps)}  shards={len(parts)}x{a.per_shard}" + (f"  slots={a.slots}" if a.slots else ""),
                  f"win% : {100.0*W/n:5.1f}   ({W}W/{L}L/{T}T)   95% Wilson [{lo:.0f}-{hi:.0f}]",
                  f"picks: {picks:5.2f} /ep", f"forms: {forms:5.2f} /ep"]
        if a.slots:
            tot = {}
            for p_ in parts:
                for s_, (w_, n_) in p_["per_slot"].items():
                    t_ = tot.setdefault(s_, [0, 0]); t_[0] += w_; t_[1] += n_
            lines.append("per-slot: " + "  ".join(f"slot{s_}={tot[s_][0]}W/{tot[s_][1]}" for s_ in sorted(tot)))
    else:
        lines += [f"[ab] model={os.path.basename(a.model)} opp={os.path.basename(a.opp)} "
                  f"episodes={n} shards={len(parts)}x{a.per_shard} (merged)"]
        lines += [f"[ab] ep {i+1}/{n}: (see shard files)" for i in range(n)]
        lines += [f"AB RESULT vs {os.path.basename(a.opp)}: {W}W/{L}L/{T}T   "
                  f"95% Wilson [{lo:.0f}-{hi:.0f}]"]
    lines += ["shard files: " + " ".join(os.path.basename(s) for s in a.shards)]
    with open(a.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"merged {len(parts)} shards -> {a.out}: {W}W/{L}L/{T}T n={n} Wilson [{lo:.0f}-{hi:.0f}]")


if __name__ == "__main__":
    main()
