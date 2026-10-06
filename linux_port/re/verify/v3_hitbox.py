"""Claims 3 + 4: are the melee hit-sphere fields (P+0x187 count, P+0x1AC.. x,y,z,r) and the hurt mask
(P+0x12C low u16) READ by the game's collision? Controlled 1v1 on slot1 (both seats human, Falcon v Falcon),
seat0 = attacker (punch X), seat1 = victim. All conditions restore the same snapshot; only the listed
RAM writes differ. Writes happen between frames (after emu.run returns)."""
import math, sys
from vcommon import *
v = V()
out = open("re/verify/v3_hitbox_out.txt", "w")
def log(*a):
    s = " ".join(str(x) for x in a); print(s); out.write(s + "\n"); out.flush()
A, B = 0, 1
PA, PB = v.P(A), v.P(B)
def place(k, x, z, y=0.0):
    P = v.P(k)
    for j, c in enumerate((x, y, z)):
        v.wf(P + 0x28 + 4*j, c); v.wf(P + 0x94 + 4*j, c)
def spheres(k):
    P = v.P(k); n = v.u8(P + 0x187)
    return [tuple(v.f32(P + 0x1AC + 0x20*j + 4*q) for q in range(4)) for j in range(max(0, n - 1))]

v.load("slot1"); v.run(2)
c0 = v.u32(0x8C475200)
for _ in range(400):
    v.run(1)
    if v.u32(0x8C475200) > c0 + 30: break
log("fight live counter", v.u32(0x8C475200), "A pos", [round(c) for c in v.pos(A)], "facing", v.u16(PA + 0x38))
BASE = v.snap()

def setup(dist):
    v.restore(BASE)
    ax, _, az = v.pos(A); a = v.u16(PA + 0x38) * 2 * math.pi / 65536
    place(B, ax + dist * math.sin(a), az + dist * math.cos(a))
    v.run(15)
    return v.snap()

def trial(S, name, hook=None, nf=45, press=BTN['x'], shot=None):
    v.restore(S)
    hp0 = v.hp(B); first_live = None; dmg_f = None; persist = []
    v.br.press(press, 1, player=A); v.br.press(0, 0, player=A)
    ctx = {}
    for f in range(1, nf):
        if hook: hook(f, ctx, 'pre')      # writes BEFORE this frame runs
        v.run(1)
        n = v.u8(PA + 0x187)
        if n > 1 and first_live is None: first_live = f
        if dmg_f is None and v.hp(B) < hp0 - 0.01: dmg_f = f
        if 'chk' in ctx:                  # did the previous write survive one frame?
            persist.append(ctx.pop('chk')())
        if hook: hook(f, ctx, 'post')
        if shot and f == shot[0]: v.shot(shot[1])
    dmg = hp0 - v.hp(B)
    log(f"  {name:38s} first_live={first_live} dmg_frame={dmg_f} dmg={dmg:.1f} victim_state_end={v.pstate(B)}"
        + (f" write_survived_next_frame={sum(persist)}/{len(persist)}" if persist else ""))
    return dmg

# ---------- baseline geometry
S100 = setup(100)
log("== baseline close punch (victim 100u in front)")
v.restore(S100); v.br.press(BTN['x'], 1, player=A); v.br.press(0, 0, player=A); hp0 = v.hp(B)
for f in range(1, 30):
    v.run(1); n = v.u8(PA + 0x187)
    if n > 1 or v.hp(B) < hp0:
        log(f"   f{f} cnt={n} spheres={[tuple(round(q) for q in s) for s in spheres(A)]} victim hp={v.hp(B):.0f} mask={v.u16(PB+0x12C):04x} vpos={[round(c) for c in v.pos(B)]}")
trial(S100, "close ctl", shot=(9, "re/verify/shots/v3_close_ctl_f9.png"))

# ---------- teleport-in design: punch whiffs at 600u; after the first live frame the victim is put onto the sphere
S600 = setup(600)
trial(S600, "whiff ctl (600u)")
def tele(extra=None):
    def h(f, ctx, ph):
        if ph != 'post': return
        if v.u8(PA + 0x187) > 1:
            if not ctx.get('t'):
                s = spheres(A)[0]; ctx['t'] = 1
                place(B, s[0], s[2])
            elif extra: extra(f, ctx)
            if extra and ctx.get('t') == 1:
                ctx['t'] = 2; extra(f, ctx)
    return h
trial(S600, "tele-in ctl", tele())
def sph_far(f, ctx):
    n = v.u8(PA + 0x187)
    for j in range(n - 1):
        v.wf(PA + 0x1AC + 0x20*j, v.f32(PA + 0x1AC + 0x20*j) + 3000.0)
    xs = v.f32(PA + 0x1AC); ctx['chk'] = lambda: abs(v.f32(PA + 0x1AC) - xs) < 1e-3
def sph_r0(f, ctx):
    n = v.u8(PA + 0x187)
    for j in range(n - 1): v.wf(PA + 0x1AC + 0x20*j + 12, 0.0)
    ctx['chk'] = lambda: v.f32(PA + 0x1AC + 12) == 0.0
def cnt1(f, ctx):
    v.w8(PA + 0x187, 1); ctx['chk'] = lambda: v.u8(PA + 0x187) == 1
def hurt_far(f, ctx):
    v.wf(PB + 0x18C, v.f32(PB + 0x18C) + 3000.0); xs = v.f32(PB + 0x18C)
    ctx['chk'] = lambda: abs(v.f32(PB + 0x18C) - xs) < 1e-3
def hurt_r0(f, ctx):
    v.wf(PB + 0x198, 0.0); v.wf(PB + 0x19C, 0.0); ctx['chk'] = lambda: v.f32(PB + 0x198) == 0.0
def mask0(f, ctx):
    v.w16(PB + 0x12C, 0); ctx['chk'] = lambda: v.u16(PB + 0x12C) == 0
for nm, fn in [("tele-in + sphere centre +3000x", sph_far), ("tele-in + sphere r=0", sph_r0),
               ("tele-in + count=1", cnt1), ("tele-in + victim hurt-cyl centre +3000x", hurt_far),
               ("tele-in + victim hurt-cyl r=h=0", hurt_r0), ("tele-in + victim mask lo16=0", mask0)]:
    trial(S600, nm, tele(fn))

# ---------- inflate during whiff
def inflate(R):
    def h(f, ctx, ph):
        if ph == 'post' and v.u8(PA + 0x187) > 1:
            for j in range(v.u8(PA + 0x187) - 1): v.wf(PA + 0x1AC + 0x20*j + 12, R)
            ctx['chk'] = lambda: v.f32(PA + 0x1AC + 12) == R
    return h
for R in (700.0, 2000.0):
    trial(S600, f"whiff + sphere r={R:.0f} every live frame", inflate(R))
def move_sph_onto_victim(f, ctx):
    pass
def sph_to_victim(f, ctx, ph):
    if ph == 'post' and v.u8(PA + 0x187) > 1:
        bx, by, bz = v.pos(B)
        v.wf(PA + 0x1AC, bx); v.wf(PA + 0x1AC + 4, by + 60); v.wf(PA + 0x1AC + 8, bz)
        ctx['chk'] = lambda: abs(v.f32(PA + 0x1AC) - bx) < 1e-3
trial(S600, "whiff + sphere centre := victim pos", sph_to_victim)

# ---------- close punch with victim mask forced 0 every frame BEFORE and during
def mask0_all(f, ctx, ph):
    if ph == 'pre': v.w16(PB + 0x12C, 0)
trial(S100, "close + victim mask lo16=0 every frame", mask0_all)
def mask0_post(f, ctx, ph):
    if ph == 'post': v.w16(PB + 0x12C, 0); ctx['chk'] = lambda: v.u16(PB + 0x12C) == 0
trial(S100, "close + victim mask lo16=0 (post-frame)", mask0_post)
def cnt1_pre(f, ctx, ph):
    if ph == 'post' and v.u8(PA + 0x187) > 1: v.w8(PA + 0x187, 1)
trial(S100, "close + count=1 after each live frame", cnt1_pre)

# ---------- claim 4b: victim invulnerable during knockdown/getup; force mask 0xFFFF
log("== getup: grab + throw the victim")
v.restore(S100)
seq = []
v.br.press(BTN['b'], 1, player=A); v.br.press(0, 0, player=A)
S14 = None
for f in range(1, 400):
    if f in (30, 40, 50): v.br.press(BTN['x'], 1, player=A); v.br.press(0, 0, player=A)
    else: v.run(1)
    st = v.pstate(B)
    if not seq or seq[-1][0] != st: seq.append((st, f, v.u16(PB + 0x12C)))
    if st == 14 and S14 is None: S14 = v.snap(); f14 = f
log("victim state sequence (state, first frame, mask):", seq)
if S14 is None:
    log("no knockdown reached; 4b skipped")
else:
    for d in range(0, 40, 3):
        v.restore(S14)
        for _ in range(d): v.run(1)
        Sd = v.snap(); vs = v.pstate(B); vm = v.u16(PB + 0x12C); ast = v.pstate(A)
        log(f" delay {d}: victim state={vs} mask={vm:04x} attacker state={ast}")
        dc = trial(Sd, f"  getup d{d} tele-in ctl", tele())
        def maskF(f, ctx, ph):
            v.w16(PB + 0x12C, 0xFFFF)
        di = trial(Sd, f"  getup d{d} tele-in + mask=FFFF every frame", tele(None) if False else (lambda f, ctx, ph: (maskF(f, ctx, ph), tele()(f, ctx, ph))))
