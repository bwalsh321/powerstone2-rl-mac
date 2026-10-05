"""Claims 3/4 follow-up. Direct writes to sphere/hurt/mask fields are overwritten every frame (v3), so here the
VICTIM's position (persistent) is the intervention. After the attacker's first live frame, the victim is placed
at a controlled offset from the reported sphere; the claim's contact test predicts hit/no-hit from the
reported fields; the game decides. Then a getup timing sweep: does the reported mask predict when hits land?"""
import math
from vcommon import *
v = V()
out = open("re/verify/v3b_geometry_out.txt", "w")
def log(*a):
    s = " ".join(str(x) for x in a); print(s); out.write(s + "\n"); out.flush()
A, B = 0, 1; PA, PB = v.P(A), v.P(B)
def place(k, x, z, y=0.0):
    P = v.P(k)
    for j, c in enumerate((x, y, z)):
        v.wf(P + 0x28 + 4*j, c); v.wf(P + 0x94 + 4*j, c)
v.load("slot1"); v.run(2)
c0 = v.u32(0x8C475200)
for _ in range(400):
    v.run(1)
    if v.u32(0x8C475200) > c0 + 30: break
BASE = v.snap()
def setup(dist, attacker_char_seat=A):
    v.restore(BASE)
    ax, _, az = v.pos(A); a = v.u16(PA + 0x38) * 2 * math.pi / 65536
    place(B, ax + dist * math.sin(a), az + dist * math.cos(a)); v.run(15)
    return v.snap()
S600 = setup(600)

def contact(sph, P):
    cx, cy, cz = v.f32(P + 0x18C), v.f32(P + 0x190), v.f32(P + 0x194); R, H = v.f32(P + 0x198), v.f32(P + 0x19C)
    x, y, z, r = sph
    return math.hypot(x - cx, z - cz) <= r + R and abs(y - cy) <= r + H

FR = dict(tp=0, fp=0, fn=0, tn=0)
def trial(press, dx, dz, y=0.0, nf=40):
    """frame-level: for each live frame after placement (up to and incl. the hit frame), contact test on the
    fields as read right after that frame vs whether the victim's hp dropped on that frame."""
    v.restore(S600)
    v.br.press(press, 1, player=A); v.br.press(0, 0, player=A)
    hp0 = v.hp(B); placed = None; pred = False; dmgf = None; info = None; marg = []
    for f in range(1, nf):
        v.run(1)
        n = v.u8(PA + 0x187)
        hit_now = dmgf is None and v.hp(B) < hp0 - 0.01
        if hit_now: dmgf = f
        if n > 1:
            sph = [tuple(v.f32(PA + 0x1AC + 0x20*j + 4*q) for q in range(4)) for j in range(n - 1)]
            if placed is not None and (dmgf is None or dmgf == f):
                c = any(contact(s_, PB) for s_ in sph); pred = pred or c
                FR[('t' if c == hit_now else 'f') + ('p' if c else 'n')] += 1
                cx, cz = v.f32(PB + 0x18C), v.f32(PB + 0x194)
                marg.append(round(min(math.hypot(s_[0]-cx, s_[2]-cz) - s_[3] - v.f32(PB + 0x198) for s_ in sph)))
            if placed is None:
                s0 = sph[0]; placed = f
                place(B, s0[0] + dx, s0[2] + dz, y)
                info = (round(s0[0]), round(s0[1]), round(s0[2]), round(s0[3]))
        if dmgf is not None and f > dmgf: break
    return info, pred, dmgf, marg

# direction of attack = attacker facing
a = v.u16(PA + 0x38) * 2 * math.pi / 65536; fx, fz = math.sin(a), math.cos(a)
dirs = {"fwd": (fx, fz), "back": (-fx, -fz), "left": (fz, -fx), "right": (-fz, fx)}
tot = agree = 0; rows = []
R = v.f32(PB + 0x198); H = v.f32(PB + 0x19C)
log(f"victim hurt cylinder R={R:.0f} H={H:.0f}")
for press, pname in ((BTN['x'], 'punch'), (BTN['y'], 'kick')):
    for dn, (ux, uz) in dirs.items():
        for d in range(40, 181, 10):
            info, pred, dmgf, marg = trial(press, d * ux, d * uz)
            hit = dmgf is not None
            tot += 1; agree += (pred == hit)
            rows.append((pname, dn, d, pred, hit))
            log(f"{pname:5s} {dn:5s} d={d:3d} sphere={info} predicted={int(pred)} game_hit={int(hit)} dmg_frame={dmgf} horiz_margins={marg}")
    for yy in (100, 150, 170, 190, 220, 260):
        info, pred, dmgf, marg = trial(press, 0, 0, y=yy)
        hit = dmgf is not None; tot += 1; agree += (pred == hit)
        log(f"{pname:5s} vertical victim_y={yy} sphere={info} predicted={int(pred)} game_hit={int(hit)} dmg_frame={dmgf} horiz_margins={marg}")
log(f"GEOMETRY: per-placement agreement {agree}/{tot}; per-frame contact test vs hit-this-frame: {FR}")
for pname in ('punch', 'kick'):
    for dn in dirs:
        hits = [d for (p, q, d, pr, h) in rows if p == pname and q == dn and h]
        preds = [d for (p, q, d, pr, h) in rows if p == pname and q == dn and pr]
        log(f"  {pname} {dn}: max hit d={max(hits) if hits else None}  max predicted d={max(preds) if preds else None}")

import sys
if len(sys.argv) > 1: sys.exit(0)
# ---- claim 4: getup timing sweep, delay by 1 frame
log("== invulnerability timing (grab-throw, then tele-in punches at every delay)")
S100 = setup(100); v.restore(S100)
v.br.press(BTN['b'], 1, player=A); v.br.press(0, 0, player=A)
S14 = None
for f in range(1, 300):
    if f in (30, 40, 50): v.br.press(BTN['x'], 1, player=A); v.br.press(0, 0, player=A)
    else: v.run(1)
    if v.pstate(B) == 14 and S14 is None: S14 = v.snap(); break
conf = dict(hit_mask0=0, hit_maskF=0, nohit_mask0=0, nohit_maskF=0)
for d in range(0, 60):
    v.restore(S14)
    for _ in range(d): v.run(1)
    v.br.press(BTN['x'], 1, player=A); v.br.press(0, 0, player=A)
    hp0 = v.hp(B); placed = False; dm = None; masks = []
    for f in range(1, 30):
        mask_before = v.u16(PB + 0x12C); st_before = v.pstate(B)
        v.run(1)
        n = v.u8(PA + 0x187)
        if placed and n > 1:
            masks.append((f, st_before, mask_before, v.u16(PB + 0x12C)))
        if v.hp(B) < hp0 - 0.01 and dm is None: dm = f
        if n > 1 and not placed:
            s = [v.f32(PA + 0x1AC + 4*q) for q in range(4)]; place(B, s[0], s[2]); placed = True
        if dm: break
    # live frames after placement: was the victim's mask (as read after that frame) zero?
    for (f, stb, mb, ma) in masks:
        hit = (dm == f)
        key = ("hit" if hit else "nohit") + ("_mask0" if ma == 0 else "_maskF")
        conf[key] += 1
    log(f" delay {d:2d}: live-frame (frame, victim state before, mask before, mask after) = {masks} dmg_frame={dm}")
log("INVULN: per live-overlap frame, mask after frame vs hit on that frame:", conf)
