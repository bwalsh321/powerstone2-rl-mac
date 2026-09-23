"""Sep 23 2026 (Astra review #3): Blake's hold thresholds, enforced by league_battery.sh
right before it advances state. Prints the hold reason (empty = no hold). Thresholds:
lv3 (slot2) < 70%, champion AB wins < 35 of 100, lv8 (slot3) < 4.0%. An unparseable
receipt also holds: the chain must never launch on evidence it cannot read."""
import re, sys

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
    if lv8 is None or lv3 is None or ab is None:
        why.append(f"unparseable receipt (lv8={lv8} lv3={lv3} ab={ab})")
    else:
        if lv3 < 70.0:
            why.append(f"lv3 {lv3:.1f} < 70 (n={n3})")
        if ab < 35:
            why.append(f"champion AB {ab} < 35")
        if lv8 < 4.0:
            why.append(f"lv8 {lv8:.1f} < 4.0 (n={n8})")
    return "; ".join(why)

if __name__ == "__main__":
    print(main(sys.argv[1], *(sys.argv[2:3])))
