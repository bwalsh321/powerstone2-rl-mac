"""Supporting screenshots only (verdicts come from the *_out.txt machine checks).
(a) item swap: slot2 melee item (type 0x06, rec64, first resting at f2193) picked by seat1 and used with X,
    ctl vs type written to 0x01 (Gun). (b) projectile: slot3 missile rec81 hitting seat3 at f1948, ctl vs moved."""
from vcommon import *
v = V()
log = open("re/verify/v7_shots_out.txt", "w")
def place(k, x, z, y=0.0):
    P = v.P(k)
    for j, c in enumerate((x, y, z)):
        v.wf(P + 0x28 + 4*j, c); v.wf(P + 0x94 + 4*j, c)
def goto(st, F):
    v.load(st); v.run(2)
    for f in range(F + 1):
        if f % 60 == 0: v.refill()
        v.run(1)
    return v.snap()
S = goto("slot2", 2193); R = v.rec(64)
for tag, w in (("ctl_type06", None), ("swap_type01", 0x01)):
    v.restore(S)
    if w: v.w8(R + 0x420, w)
    v.refill(); place(1, v.f32(R + 0x2C), v.f32(R + 0x34) + 30.0); v.run(2)
    for b in ('b', 'y'):
        v.br.press(BTN[b], 1, player=1); v.br.press(0, 0, player=1); v.run(40)
        if v.heldptr(1): break
    v.run(30)
    v.br.press(BTN['x'], 1, player=1); v.br.press(0, 0, player=1)
    for f in range(1, 40):
        v.run(1)
        if f in (12, 24): v.shot(f"re/verify/shots/v7_item_{tag}_x{f}.png")
    t = v.table(); c1 = [hex(int(t['vt'][i])) for i in np.nonzero(t['cat'] == 1)[0]]
    log.write(f"{tag}: held type {v.u8(R + 0x420):#x} uses {v.u16(R + 0x424)} live cat1 now {c1}\n")
S = goto("slot3", 1948 - 4); R = v.rec(81)
for tag in ("ctl", "moved"):
    v.restore(S); hp = v.hp(3)
    for d in range(6):
        if tag == "moved": v.wf(R + 0x30, 5000.0); v.wf(R + 0x9C, 5000.0)
        v.run(1)
        if d == 3: v.shot(f"re/verify/shots/v7_proj_{tag}_hitframe.png")
    log.write(f"proj {tag}: seat3 hp loss {hp - v.hp(3):.0f}\n")
log.close(); print(open("re/verify/v7_shots_out.txt").read())
