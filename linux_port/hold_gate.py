"""Sep 23 2026 (Astra review #3): Blake's hold thresholds, enforced by league_battery.sh
right before it advances state. Prints the hold reason (empty = no hold). Thresholds:
lv3 (slot2) < 70%, champion AB wins < 35 of 100, lv8 (slot3) < 4.0%. An unparseable
receipt also holds: the chain must never launch on evidence it cannot read."""
import os, re, sys

LV8MIX_FLOOR = float(os.environ.get("PS2_LV8MIX_FLOOR", "20"))


def wins(path):
    try:
        t = open(path).read()
    except OSError:
        return None, 0
    m = re.search(r"win% :\s*([\d.]+)\s*\((\d+)W/(\d+)L/(\d+)T\)", t)
    return (float(m.group(1)), int(m.group(2)) + int(m.group(3)) + int(m.group(4))) if m else (None, 0)

def main(n, root="receipts"):
    why = []
    lv8, n8 = wins(f"{root}/eval_leg{n}_slot3_out.txt")
    lv3, n3 = wins(f"{root}/eval_leg{n}_slot2_out.txt")
    ab = None
    try:
        m = re.search(r"AB RESULT vs \S+: (\d+)W/(\d+)L", open(f"{root}/eval_leg{n}_ab_vs_leg1_out.txt").read())
        ab = int(m.group(1)) if m else None
    except OSError:
        pass
    # Oct 1 2026 (Blake dropped the lv3 eval): the lv3 threshold applies only when a slot2 receipt exists.
    has_lv3 = os.path.exists(f"{root}/eval_leg{n}_slot2_out.txt")
    # Oct 2 2026 (Blake dropped the per-leg trio and champion AB): each threshold applies only when its receipt
    # exists; the lv8mix floor below is the standing per-leg gate.
    has_lv8 = os.path.exists(f"{root}/eval_leg{n}_slot3_out.txt")
    has_ab = os.path.exists(f"{root}/eval_leg{n}_ab_vs_leg1_out.txt")
    if (has_lv8 and lv8 is None) or (has_lv3 and lv3 is None) or (has_ab and ab is None):
        why.append(f"unparseable receipt (lv8={lv8} lv3={lv3} ab={ab})")
    else:
        if has_lv3 and lv3 < 70.0:
            why.append(f"lv3 {lv3:.1f} < 70 (n={n3})")
        if has_ab and ab < 35:
            why.append(f"champion AB {ab} < 35")
        if has_lv8 and lv8 < 4.0:
            why.append(f"lv8 {lv8:.1f} < 4.0 (n={n8})")
    # Oct 2 2026 (Blake: lv8mix is the number that matters): floor on the held-out set. Applies when its receipt
    # exists (the battery runs it unless PS2_LV8MIX=0); 20% at n=1000 only trips on a collapse (series low 26.4).
    mix, nm = wins(f"{root}/eval_leg{n}_lv8mix_out.txt")
    if not os.path.exists(f"{root}/eval_leg{n}_lv8mix_out.txt") and os.environ.get("PS2_LV8MIX", "1") == "1":
        why.append("missing lv8mix receipt (the per-leg grade)")
    if os.path.exists(f"{root}/eval_leg{n}_lv8mix_out.txt"):
        if mix is None:
            why.append("unparseable lv8mix receipt")
        elif mix < LV8MIX_FLOOR:
            why.append(f"lv8mix {mix:.1f} < {LV8MIX_FLOOR:g} (n={nm})")
        else:
            # Oct 7 2026 (audit): the 20% floor is far below the ~45% the bot now plays at. Also hold when a leg falls
            # more than PS2_DROP_HOLD points (default 6, ~2.8 SE of a difference at n=1000) below the best of the
            # previous 5 graded legs.
            prev = [wins(f"{root}/eval_leg{k}_lv8mix_out.txt")[0] for k in range(int(n) - 5, int(n))]
            prev = [p for p in prev if p is not None]
            drop = float(os.environ.get("PS2_DROP_HOLD", "6"))
            if prev and mix < max(prev) - drop:
                why.append(f"lv8mix {mix:.1f} is more than {drop:g} below the best of the last {len(prev)} legs ({max(prev):.1f})")
        # Oct 7 2026 (audit): too few distinct rounds = the eval replayed itself (seed bug class); real legs show ~800+.
        try:
            m_ = re.search(r"distinct-episodes=(\d+)", open(f"{root}/eval_leg{n}_lv8mix_out.txt").read())
            if m_ and int(m_.group(1)) < int(os.environ.get("PS2_MIN_DISTINCT", "600")):
                why.append(f"only {m_.group(1)} distinct rounds of {nm} (the eval repeated itself)")
        except OSError:
            pass
    return "; ".join(why)

if __name__ == "__main__":
    print(main(sys.argv[1], *(sys.argv[2:3])))
