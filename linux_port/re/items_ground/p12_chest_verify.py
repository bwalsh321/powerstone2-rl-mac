"""p12: verify chest content byte from a p10 verbose log. A chest's content
(+0x42C, 5th tuple element) dropping X->0 at frame f must coincide with a
NEW category-9 object at frame f (+-4) at the chest's xz whose type id
(+0x420, 3rd tuple element) == X."""
import re, sys, math, collections
chg = re.compile(r"f=\s*(\d+) idx=\s*(-?\d+) chg\s+\((\d+), (\d+), (\d+), (\d+), (\d+)\) -> \((\d+), (\d+), (\d+), (\d+), (\d+)\)\s+pos=\((-?\d+), (-?\d+), (-?\d+)\)")
new = re.compile(r"f=\s*(\d+) idx=\s*(-?\d+) NEW\s+\((\d+), (\d+), (\d+), (\d+), (\d+), (\d+), (-?\d+), (-?\d+), (-?\d+)\)")
lines = open(sys.argv[1]).read().splitlines()
news = []
for l in lines:
    m = new.search(l)
    if m:
        g = list(map(int, m.groups())); news.append(g)
ok = bad = miss = 0; tally = collections.Counter()
for l in lines:
    m = chg.search(l)
    if not m: continue
    g = list(map(int, m.groups()))
    f, idx = g[0], g[1]
    if g[3] == 194 and g[8] == 194 and g[6] != 0 and g[11] == 0:
        X = g[6]; cx, cz = g[12], g[14]
        cand = [n for n in news if abs(n[0] - f) <= 4 and math.hypot(n[8] - cx, n[10] - cz) < 60]
        if not cand:
            miss += 1; print(f"f={f} chest ({cx},{cz}) content={X:#x} -> no spawn"); continue
        n = cand[0]; vt, tid = n[2], n[4]
        good = tid == X; ok += good; bad += not good; tally[(X, vt)] += 1
        print(f"f={f} chest ({cx},{cz}) content={X:#04x} -> spawn vt={vt:#x} id={tid:#04x} y={n[9]} {'MATCH' if good else 'MISMATCH'}")
print(f"MATCH={ok} MISMATCH={bad} NOSPAWN={miss}")
print("content -> vt:", {f"{x:#x}": f"{v:#x}" for (x, v) in tally})
