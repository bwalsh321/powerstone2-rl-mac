"""Claim 2: held type = u8[(F+0x54)-4+0x420]; uses counter u16 +0x424; item table 0x0C273900+(code-1)*0x34 +6.
Phase A: slot2/slot3 COM matches (seat1 = idle human Falcon), find natural resting ground items (state 2,
generic item vt), snapshot each. Phase B per item: conditions ctl / type swapped (+0x420 only, written before
pickup). Seat1 is teleported onto the item and presses B (pick up). Then: hold idle 60 f, press X once, watch
60 f. Machine checks: held ptr == rec+4; held type; uses at pickup vs table; uses ticking; new cat-1 records
spawned (bullets) and live melee spheres on seat1."""
import sys, math
from vcommon import *
v = V()
out = open("re/verify/v2_items_out.txt", "w")
def log(*a):
    s = " ".join(str(x) for x in a); print(s); out.write(s + "\n"); out.flush()
GUNS = {0x01, 0x02, 0x0C, 0x0D, 0x33, 0x39, 0x3B}
MELEE = {0x04, 0x05, 0x06, 0x07, 0x19, 0x1D, 0x2B, 0x13}
def tab(code): return v.u16(0x8C273900 + (code - 1) * 0x34 + 6)
K = 1; PK = v.P(K)
def place(k, x, z, y=0.0):
    P = v.P(k)
    for j, c in enumerate((x, y, z)):
        v.wf(P + 0x28 + 4*j, c); v.wf(P + 0x94 + 4*j, c)

events = []
for st in ["slot2", "slot3"]:
    v.load(st); v.run(2); seen = set()
    for f in range(12000):
        if f % 60 == 0: v.refill()
        v.run(1)
        if f % 3: continue
        t = v.table()
        for i in np.nonzero((t['cat'] == 9) & (t['st'] == 2) & (t['vt'] == 0x0C0C9810))[0]:
            key = (int(i), int(t['ser'][i]))
            if key in seen: continue
            seen.add(key)
            tid = int(t['tid'][i])
            kind = 'gun' if tid in GUNS else 'melee' if tid in MELEE else None
            if kind and sum(e['kind'] == kind for e in events) < 6:
                events.append(dict(st=st, f=f, i=int(i), ser=key[1], tid=tid, kind=kind, uses=int(t['uses'][i]), blob=v.snap()))
    log(f"{st}: items collected so far {[(e['kind'], hex(e['tid'])) for e in events]}")
log("table counters:", {hex(c): tab(c) for c in sorted(GUNS | MELEE)})

def trial(e, newtid, tag):
    v.restore(e['blob']); r = v.rec(e['i'])
    if newtid is not None: v.w8(r + 0x420, newtid)
    want = e['tid'] if newtid is None else newtid
    v.refill()
    place(K, v.f32(r + 0x2C), v.f32(r + 0x34) + 30.0)
    v.run(2)
    got = None
    for btn in ('b', 'x', 'y'):
        v.br.press(BTN[btn], 1, player=K); v.br.press(0, 0, player=K)
        for f in range(40):
            v.run(1)
            if v.heldptr(K) == ((r + 4) & 0x0FFFFFFF) | 0x0C000000 or (v.heldptr(K) & 0xFFFFFF) == ((r + 4) & 0xFFFFFF):
                got = btn; break
        if got: break
    if not got:
        log(f"  {tag}: NO PICKUP (heldptr={v.heldptr(K):08x}, rec tid now {v.u8(r+0x420):#x} st {v.u8(r+0x421)})")
        return None
    held_t = v.u8(((v.heldptr(K) - 4) | 0x80000000) + 0x420)
    u0 = v.u16(r + 0x424)
    # idle hold
    us = [u0]
    for f in range(60):
        if f % 30 == 0: v.refill()
        v.run(1); us.append(v.u16(r + 0x424) if v.heldptr(K) else -1)
    t0 = v.table(); keys0 = {(i, int(t0['ser'][i])) for i in np.nonzero(t0['cat'])[0]}
    ub = v.u16(r + 0x424)
    v.br.press(BTN['x'], 1, player=K); v.br.press(0, 0, player=K)
    new_cat1 = []; live_sph = 0; acts = set(); states = set()
    for f in range(60):
        if f % 30 == 0: v.refill()
        v.run(1)
        t = v.table()
        for i in np.nonzero(t['cat'] == 1)[0]:
            if (i, int(t['ser'][i])) not in keys0:
                keys0.add((i, int(t['ser'][i]))); new_cat1.append(hex(int(t['vt'][i])))
        live_sph += v.u8(PK + 0x187) > 1
        acts.add(hex(v.u16(PK + 0x3818))); states.add(v.pstate(K))
    ua = v.u16(r + 0x424)
    idle_d = [b - a for a, b in zip(us, us[1:]) if a >= 0 and b >= 0]
    log(f"  {tag}: pickup_btn={got} held_type={held_t:#x} (expected {want:#x}) uses@pickup={u0} table[orig {e['tid']:#x}]={tab(e['tid'])} "
        f"table[written {want:#x}]={tab(want)} ground_uses_before={e['uses']} | idle60 uses delta={us[-1]-us[0]} (per-frame -1 count={idle_d.count(-1)}) "
        f"| after X: uses {ub}->{ua} new_cat1={new_cat1} sphere_live_frames={live_sph} seat1_states={sorted(states)} acts={sorted(acts)[:8]}")
    if tag.endswith("ev0 ctl") or tag.endswith("ev0 swap"):
        pass
    return dict(held=held_t, want=want, u0=u0, idle=us[-1]-us[0], shots=ua-ub, cat1=new_cat1, sph=live_sph)

res = []
for n, e in enumerate(events):
    log(f"ev{n} {e['st']} f{e['f']} rec{e['i']} natural type {e['tid']:#x} ({e['kind']}) ground uses {e['uses']}")
    swap = 0x05 if e['kind'] == 'gun' else 0x01
    a = trial(e, None, f"ev{n} ctl")
    b = trial(e, swap, f"ev{n} swap->{swap:#x}")
    res.append((e, a, b))
log("SUMMARY")
for e, a, b in res:
    log(f" {e['kind']:5s} {e['tid']:#x}: ctl={a and {k: a[k] for k in ('held','u0','idle','shots','sph')}} ncat1={a and len(a['cat1'])} | "
        f"swap={b and {k: b[k] for k in ('held','want','u0','idle','shots','sph')}} ncat1={b and len(b['cat1'])}")
