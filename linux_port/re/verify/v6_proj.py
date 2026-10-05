"""Claim 6: category-1 ledger records are live hit volumes. Natural 4P COM fights (slot3 lv8, slot2 lv3),
seat1 idle, health refilled every 60 f. Phase A finds hits whose victim hit-source pointer P+0x3774 ==
ledger record+4 of a category-1 record that already existed >= LEAD frames before the hit. Phase B
replays (deterministic) to hit-LEAD and runs conditions: ctl / move record +5000 y (pos + matrix, every
frame) / zero header low byte (once) / move pos only (every frame). Machine check: did the victim lose hp
with source == that record, and total victim hp loss in the window."""
import sys
from vcommon import *
LEAD = int(sys.argv[1]) if len(sys.argv) > 1 else 4
NMAX = int(sys.argv[2]) if len(sys.argv) > 2 else 12
v = V()
out = open("re/verify/v6_proj_out.txt", "w")
def log(*a):
    s = " ".join(str(x) for x in a); print(s); out.write(s + "\n"); out.flush()
G = GRID & 0xFFFFFF
def src_rec(k):
    p = v.u32(v.P(k) + 0x3774) & 0xFFFFFF
    if G <= p - 4 < G + 208*STRIDE and (p - 4 - G) % STRIDE == 0: return (p - 4 - G) // STRIDE
    return None
events = []
for st, NF in [("slot3", 9000), ("slot2", 9000)]:
    v.load(st); v.run(2)
    hist = []   # per frame: dict idx->(cat, ser)
    hp = [v.hp(k) for k in range(4)]
    for f in range(NF):
        if f % 60 == 0: v.refill(); hp = [v.hp(k) for k in range(4)]
        v.run(1)
        t = v.table()
        hist.append({i: (int(t['cat'][i]), int(t['ser'][i]), int(t['vt'][i])) for i in np.nonzero(t['cat'])[0]})
        for k in range(4):
            h = v.hp(k)
            if h < hp[k] - 0.01:
                i = src_rec(k)
                if i is not None and i in hist[-1] and hist[-1][i][0] == 1 and f >= LEAD:
                    cat, ser, vt = hist[-1][i]
                    if all(hist[f - d].get(i, (0, -1))[:2] == (1, ser) for d in range(LEAD + 1)):
                        if not any(e['st'] == st and e['i'] == i and e['ser'] == ser for e in events):
                            events.append(dict(st=st, f=f, k=k, i=i, ser=ser, vt=vt, dmg=hp[k] - h))
            hp[k] = h
        if len(hist) > LEAD + 2: hist[-LEAD - 3] = None
    log(f"{st}: qualifying cat-1 hit events so far {len(events)}")
events = events[:NMAX] if len(events) <= NMAX else [events[j] for j in np.linspace(0, len(events)-1, NMAX).astype(int)]
log("events:", [(e['st'], e['f'], e['k'], e['i'], hex(e['vt']), round(e['dmg'])) for e in events])

# phase B: snapshots by deterministic replay
snaps = {}
for st in sorted(set(e['st'] for e in events)):
    want = sorted({e['f'] - LEAD for e in events if e['st'] == st})
    v.load(st); v.run(2)
    for f in range(max(want) + 1):
        if f % 60 == 0: v.refill()
        v.run(1)
        if f in want: snaps[(st, f)] = v.snap()

def run_cond(e, cond):
    v.restore(snaps[(e['st'], e['f'] - LEAD)])
    r = v.rec(e['i'])
    ok_pre = v.u8(r + 4) == 1 and v.u32(r + 0x28) == e['ser']
    hp = v.hp(e['k']); from_rec = 0; tot = 0.0
    if cond == 'hdr0': v.w8(r + 4, 0)
    for d in range(LEAD + 8):
        f = e['f'] - LEAD + d + 1
        if cond in ('far', 'farpos') and v.u32(r + 0x28) == e['ser']:
            for j, off in enumerate((0x2C, 0x30, 0x34)):
                if j == 1: v.wf(r + off, 5000.0)
            if cond == 'far': v.wf(r + 0x9C, 5000.0)
        if f % 60 == 0: v.refill(); hp = v.hp(e['k'])
        v.run(1)
        h = v.hp(e['k'])
        if h < hp - 0.01:
            tot += hp - h
            if src_rec(e['k']) == e['i']: from_rec += 1
        hp = h
    return ok_pre, from_rec, tot

summ = {c: [0, 0] for c in ('ctl', 'far', 'farpos', 'hdr0')}
for n, e in enumerate(events):
    row = []
    for c in ('ctl', 'far', 'farpos', 'hdr0'):
        ok_pre, fr, tot = run_cond(e, c)
        row.append(f"{c}: pre_ok={ok_pre} hits_from_rec={fr} victim_dmg={tot:.0f}")
        summ[c][0] += 1; summ[c][1] += fr > 0
    log(f"ev{n} {e['st']} f{e['f']} victim=seat{e['k']} rec={e['i']} vt={e['vt']:#x} natural_dmg={e['dmg']:.0f} | " + " | ".join(row))
log("SUMMARY (events, events where the record still hit the victim):", summ)
