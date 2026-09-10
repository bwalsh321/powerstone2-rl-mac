#!/usr/bin/env python3
"""Validate an evaluation receipt before the relay is allowed to act on it.

The league relay used to treat "the output file contains a marker string"
as proof an evaluation ran. It is not: every eval on macOS dies with a
libc++ mutex abort AFTER printing its summary (so exit status is useless),
and a crashed eval can leave a partial file. This script is the single
definition of "a complete receipt" for both eval kinds.

    check_receipt.py slot  <file> --model <zip> --episodes N
    check_receipt.py ab    <file> --model <zip> --opp <zip> --episodes N

Exit 0 = complete and consistent. Exit 1 = anything else (reason on stderr).
Stdlib only; runs anywhere.
"""
import argparse
import os
import re
import sys


def fail(msg):
    print(f"RECEIPT INVALID: {msg}", file=sys.stderr)
    sys.exit(1)


def read(path):
    if not os.path.isfile(path):
        fail(f"{path}: missing")
    with open(path, errors="replace") as f:
        return f.read()


def check_slot(args):
    text = read(args.file)
    m = re.search(r"model=(\S+)\s+slot=(\d+)\s+n=(\d+)", text)
    if not m:
        fail("no summary header (model=/slot=/n=)")
    model, n = m.group(1), int(m.group(3))
    want = os.path.basename(args.model)
    if model != want:
        fail(f"summary is for {model}, expected {want}")
    if n != args.episodes:
        fail(f"summary n={n}, expected {args.episodes}")
    w = re.search(r"win%\s*:\s*[\d.]+\s*\((\d+)W/(\d+)L/(\d+)T\)", text)
    if not w:
        fail("no win% line")
    tot = sum(int(x) for x in w.groups())
    if tot != args.episodes:
        fail(f"W+L+T={tot}, expected {args.episodes}")
    if not re.search(r"picks:\s*[\d.]+", text) or not re.search(r"forms:\s*[\d.]+", text):
        fail("picks/forms lines missing")
    print(f"receipt ok: {os.path.basename(args.file)} "
          f"{w.group(1)}W/{w.group(2)}L/{w.group(3)}T n={n}")


def check_ab(args):
    text = read(args.file)
    want_opp = os.path.basename(args.opp)
    m = re.search(r"AB RESULT vs (\S+):\s*(\d+)W/(\d+)L/(\d+)T", text)
    if not m:
        fail("no 'AB RESULT vs <opp>: aW/bL/cT' line")
    if m.group(1) != want_opp:
        fail(f"AB result is vs {m.group(1)}, expected {want_opp}")
    tot = sum(int(x) for x in m.groups()[1:])
    if tot != args.episodes:
        fail(f"W+L+T={tot}, expected {args.episodes}")
    # the probe prints the candidate it loaded; require it when present
    lm = re.search(r"\[ab\]\s*model=(\S+)", text)
    if lm and lm.group(1) != os.path.basename(args.model):
        fail(f"probe loaded {lm.group(1)}, expected {os.path.basename(args.model)}")
    n_eps = len(re.findall(r"\[ab\] ep \d+/\d+:", text))
    if n_eps != args.episodes:
        fail(f"{n_eps} per-episode lines, expected {args.episodes}")
    print(f"receipt ok: {os.path.basename(args.file)} "
          f"{m.group(2)}W/{m.group(3)}L/{m.group(4)}T vs {want_opp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["slot", "ab"])
    ap.add_argument("file")
    ap.add_argument("--model", required=True)
    ap.add_argument("--opp")
    ap.add_argument("--episodes", type=int, required=True)
    args = ap.parse_args()
    if args.kind == "slot":
        check_slot(args)
    else:
        if not args.opp:
            fail("--opp required for ab")
        check_ab(args)


if __name__ == "__main__":
    main()
