"""Claim 1: chest content byte +0x42C decides what spawns. Controlled A/B from identical snapshots.
Phase A: baseline run on slot2/slot3 (P2 idle, COMs open chests), find chest events, snapshot each chest
shortly after birth. Phase B: for each event, restore and run conditions {control, 0xC1, 0x02, 0x05, 0x0C}
writing ONLY +0x42C once; record every NEW ledger record (new idx/serial) within 150 u xz of the chest
in the 120 frames after the chest enters state 9."""
import sys, time
from vcommon import *
CHEST_VT = 0x0C0CC7A8
v = V()
ONLY = sys.argv[2] if len(sys.argv) > 2 else None
out = open(f"re/verify/v1_chest_out{'_'+ONLY if ONLY else ''}.txt", "w")
def log(*a):
    s = " ".join(str(x) for x in a); print(s); out.write(s + "\n"); out.flush()

def live_keys(t):
    return {(i, int(t['ser'][i])) for i in range(208) if t['cat'][i] != 0}

def follow(chest_i, chest_ser, maxf, shotpath=None):
    """run until the chest opens; return (open_frame, content_at_open_minus1, spawns list)"""
    t = v.table(); prev = live_keys(t)
    opened = None; spawns = []; cx = cz = None; last_content = None
    for f in range(maxf):
        if f % 60 == 0: v.refill()
        v.run(1)
        t = v.table(); keys = live_keys(t)
        alive = t['cat'][chest_i] != 0 and int(t['ser'][chest_i]) == chest_ser and int(t['vt'][chest_i]) == CHEST_VT
        if alive:
            cx, cz = float(t['x'][chest_i]), float(t['z'][chest_i])
            if t['content'][chest_i]: last_content = int(t['content'][chest_i])
            if opened is None and t['st'][chest_i] == 9: opened = f
        if opened is None and not alive:
            opened = f  # vanished without state 9
        if opened is not None:
            for (i, s) in keys - prev:
                if t['cat'][i] == 9 and cx is not None and np.hypot(t['x'][i]-cx, t['z'][i]-cz) < 150:
                    spawns.append(dict(f=f, i=i, vt=int(t['vt'][i]), tid=int(t['tid'][i]), st=int(t['st'][i])))
            if shotpath and f == opened + 45: v.shot(shotpath)
            if f > opened + 120: break
        prev = keys
    return opened, last_content, spawns

events = []
T0 = time.time()
for st in ([ONLY] if ONLY else ["slot2", "slot3"]):
    v.load(st); v.run(2)
    t = v.table(); known = set()
    for f in range(14000):
        if f % 60 == 0: v.refill()
        v.run(1)
        if f % 2: continue
        t = v.table()
        for i in np.nonzero((t['vt'] == CHEST_VT) & (t['cat'] == 9))[0]:
            key = (st, int(i), int(t['ser'][i]))
            if key in known: continue
            known.add(key)
            if t['st'][i] == 2 and len(events) < 99:
                events.append(dict(st=st, f=f, i=int(i), ser=int(t['ser'][i]), content=int(t['content'][i]),
                                   x=float(t['x'][i]), z=float(t['z'][i]), blob=v.snap()))
    log(f"{st}: chests seen {len(known)}  t={time.time()-T0:.0f}s")
log(f"total chest events with snapshot: {len(events)}")

CONDS = [None, 0xC1, 0x02, 0x05, 0x0C]
NEV = int(sys.argv[1]) if len(sys.argv) > 1 else 8
summary = {c: [0, 0, 0] for c in CONDS}   # [trials, match, opened]
used = 0
for ev in events:
    if used >= NEV: break
    res = {}
    for c in CONDS:
        v.restore(ev['blob'])
        if c is not None:
            v.w8(v.rec(ev['i']) + 0x42C, c)
        pred = ev['content'] if c is None else c
        shp = f"re/verify/shots/v1_{ev['st']}_ev{used}_{'ctl' if c is None else hex(c)}.png" if used < 2 else None
        opened, lastc, spawns = follow(ev['i'], ev['ser'], 4000, shp)
        tids = [s['tid'] for s in spawns]
        ok = opened is not None and len(spawns) >= 1 and spawns[0]['tid'] == pred
        res[c] = (opened, lastc, spawns)
        if c is None and opened is None: break
        summary[c][0] += 1; summary[c][2] += opened is not None; summary[c][1] += ok
        log(f"ev{used} {ev['st']} birthf={ev['f']} idx={ev['i']} natural_content={ev['content']:#x} cond={'ctl' if c is None else hex(c)} "
            f"pred={pred:#x} opened@{opened} content_before_open={lastc if lastc is None else hex(lastc)} "
            f"spawns={[(s['f'], hex(s['vt']), hex(s['tid']), s['st']) for s in spawns]} -> {'MATCH' if ok else 'MISMATCH'}")
    if res.get(None, (None,))[0] is not None: used += 1
log("SUMMARY cond: trials, match, opened")
for c in CONDS: log(f"  {'ctl' if c is None else hex(c)}: {summary[c]}")
log(f"time {time.time()-T0:.0f}s")
