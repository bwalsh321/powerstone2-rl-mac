"""Does the counter persist across drop -> re-pickup (same record, same code)?
And does it tick while the item lies on the ground? Compares end ctr of a hold
with the init ctr of the next hold of the same record/code, with the gap."""
import json, glob, collections
NAMES = json.load(open("item_names.json"))
rows = []
for f in sorted(glob.glob("ev/holds_*.json")):
    d = json.load(open(f)); H = collections.defaultdict(list)
    for h in d["holds"]:
        if h.get("end_info"): H[h["o"]].append(h)
    for o, L in H.items():
        L.sort(key=lambda h: h["start"])
        for a, b in zip(L, L[1:]):
            ca, cb = a["info"]["code"] & 0xFF, b["info"]["code"] & 0xFF
            if ca == cb and ca < 0xC1 and b["start"] - a["end"] < 600:
                rows.append((NAMES[ca-1], a["end_info"]["ctr"], b["info"]["ctr"], b["start"] - a["end"]))
same = sum(1 for r in rows if r[1] == r[2])
print(f"re-pickups of the same record within 600 f: {len(rows)}; counter unchanged across the gap: {same}")
for r in rows[:40]: print("  %-16s end=%4d next_init=%4d gap=%3d f" % r)
