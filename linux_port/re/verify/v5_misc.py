"""Claim 5 (stage id 0x8C472CF8 constancy) + claim-2 follow-up (when is the uses counter initialised?)."""
from vcommon import *
v = V()
out = open("re/verify/v5_misc_out.txt", "w")
def log(*a):
    s = " ".join(str(x) for x in a); print(s); out.write(s + "\n"); out.flush()
# ---- stage id
lo, hi = 0x46E000, 0x476000
const_mask = None; first = None
for st in ["slot1", "slot2", "slot3"]:
    v.load(st); v.run(2); vals = set(); mir = set()
    ref = np.frombuffer(bytes(v.ram[lo:hi]), '<u4').copy(); same = np.ones_like(ref, bool)
    for f in range(6000):
        if f % 60 == 0: v.refill()
        v.run(1)
        if f % 10 == 0:
            vals.add(v.u32(0x8C472CF8)); mir.add(v.u32(0x8C46E198))
            same &= np.frombuffer(bytes(v.ram[lo:hi]), '<u4') == ref
    n5 = int(np.sum(same & (ref == 5)))
    log(f"{st}: 0x8C472CF8 values over 6000 f = {sorted(vals)}; mirror 0x8C46E198 = {sorted(mir)}; "
        f"other constant u32 == 5 in 0x8C46E000-0x8C476000: {n5 - 2 if 5 in vals else n5}")
# ---- uses init at spawn: force chest contents, read the spawned record's +0x424 at its first frame
TAB = lambda c: v.u16(0x8C273900 + (c - 1) * 0x34 + 6)
v.load("slot2"); v.run(2); snaps = []; seen = set()
for f in range(3000):
    if f % 60 == 0: v.refill()
    v.run(1)
    t = v.table()
    for i in np.nonzero((t['vt'] == 0x0C0CC7A8) & (t['cat'] == 9) & (t['st'] == 2))[0]:
        if (i, int(t['ser'][i])) not in seen and len(snaps) < 3:
            seen.add((i, int(t['ser'][i]))); snaps.append((int(i), int(t['ser'][i]), v.snap()))
ok = tot = 0
for (ci, ser, blob) in snaps:
    for c in (0x01, 0x02, 0x05, 0x0C, 0x33, 0x04):
        v.restore(blob); v.w8(v.rec(ci) + 0x42C, c)
        t = v.table(); prev = {(i, int(t['ser'][i])) for i in np.nonzero(t['cat'])[0]}
        cx, cz = float(t['x'][ci]), float(t['z'][ci]); res = None
        for f in range(4000):
            if f % 60 == 0: v.refill()
            v.run(1); t = v.table()
            for i in np.nonzero(t['cat'] == 9)[0]:
                k = (i, int(t['ser'][i]))
                if k not in prev and t['tid'][i] == c and np.hypot(t['x'][i]-cx, t['z'][i]-cz) < 150:
                    res = (int(t['uses'][i]), int(t['st'][i])); break
            if res: break
            prev = {(i, int(t['ser'][i])) for i in np.nonzero(t['cat'])[0]}
        tot += 1; ok += bool(res and res[0] == TAB(c))
        log(f" chest rec{ci} forced {c:#x}: spawned uses at first frame={res and res[0]} (state {res and res[1]}) table={TAB(c)}")
log(f"USES-AT-SPAWN == table: {ok}/{tot}")
