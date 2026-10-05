"""Per item code: counter semantics + what happens after release.
 - init counters seen (pickup of a fresh item has ctr == table counter)
 - tick style: 'per-frame' if most counter changes are -1 on consecutive frames,
   'per-use' if changes are separated by gaps; holder state bytes at the ticks
 - release: displacement over the first 12 frames post-release (thrown => large),
   and the code/state word sequence after release (e.g. bomb -> 0xc6 explosion)"""
import json, glob, sys, collections, math
NAMES = json.load(open("item_names.json"))
def nm(c): return NAMES[c-1] if 1 <= c <= len(NAMES) else f"<0x{c:02x}>"
by = collections.defaultdict(list)
for f in sorted(glob.glob("ev/holds_*.json")):
    d = json.load(open(f))
    for h in d["holds"]:
        by[h["info"]["code"] & 0xFF].append((d["tag"], h))
for c in sorted(by):
    L = by[c]
    inits = collections.Counter(h["info"]["ctr"] for _, h in L)
    gaps = []; sts = collections.Counter(); ends = collections.Counter()
    disp = []; postcodes = collections.Counter(); durs = []
    for _, h in L:
        cl = h["ctr_log"]
        for a, b in zip(cl, cl[1:]):
            gaps.append(b[0] - a[0]); sts[b[2]] += 1
        if h.get("end_info"): ends[h["end_info"]["ctr"]] += 1
        if h["end"] is not None: durs.append(h["end"] - h["start"])
        p = h["post"]
        if len(p) >= 4 and p[0][1:4] != [0, 0, 0]:
            d = math.dist(p[0][1:4], p[3][1:4]); disp.append(round(d))
            postcodes[tuple(sorted(set(f"{x[4]:#x}" for x in p)))] += 1
    style = "none"
    if gaps:
        one = sum(1 for g in gaps if g == 1) / len(gaps)
        style = "per-frame" if one > 0.8 else ("per-use" if one < 0.3 else f"mixed({one:.2f})")
    print(f"{c:#04x} {nm(c):18s} n={len(L):3d} init={dict(inits.most_common(4))} tick={style} "
          f"tick_states={dict(sts.most_common(4))} end_ctr={dict(ends.most_common(3))} "
          f"dur_med={sorted(durs)[len(durs)//2] if durs else None} post12f_disp={sorted(disp)[-6:]} post_codes={dict(postcodes.most_common(3))}")
