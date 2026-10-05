from vcommon import *
v = V()
for st in ["slot1", "slot2", "slot3"]:
    v.load(st); v.run(2)
    print("==", st, "stage", v.u32(0x8C472CF8))
    for k in range(4):
        print(f" seat{k} char={v.char(k)} com={v.com(k)} hp={v.hp(k):.0f} pos={tuple(round(c) for c in v.pos(k))} st={v.pstate(k)} held={v.heldptr(k):08x} hurt={v.u32(v.P(k)+0x12C):08x} cnt={v.u8(v.P(k)+0x187)}")
    for r in v.records():
        if r['cat'] in (1, 9): print("  ", {k: (hex(x) if k in ('vt','a') else (round(x) if isinstance(x,float) else x)) for k, x in r.items()})
# determinism
v.load("slot2"); v.run(300); h1 = v.ramhash()
v.load("slot2"); v.run(300); h2 = v.ramhash()
b = v.snap(); v.run(300); h3 = v.ramhash(); v.restore(b); v.run(300); h4 = v.ramhash()
print("determinism load->300:", h1 == h2, " snap/restore->300:", h3 == h4)
v.shot("re/verify/shots/v0_test.png")
fr = v.br.emu.get_frame(); print(type(fr), getattr(fr, 'shape', None))
