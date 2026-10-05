"""Decode the game's own item property table (found by find_proptable.py).
Entry i (item_no i, held-object code byte = i+1) at ITEM_TAB + i*0x34.
usage: decode_table.py <ram dump .bin> [out.json]"""
import sys, json, struct
ITEM_TAB = 0x0C273900
STRIDE = 0x34
NAME_PTRS = 0x0C29DDD0
r = open(sys.argv[1], "rb").read()
def b(a): return r[a & 0xFFFFFF]
def h(a): return struct.unpack_from("<H", r, a & 0xFFFFFF)[0]
def w(a): return struct.unpack_from("<I", r, a & 0xFFFFFF)[0]
def f(a): return struct.unpack_from("<f", r, a & 0xFFFFFF)[0]
def s(a):
    o = a & 0xFFFFFF; return r[o:r.index(b"\0", o)].decode("latin1")
rows = []
for i in range(121):
    e = ITEM_TAB + i * STRIDE
    rows.append(dict(
        no=i, code=i + 1, name=s(w(NAME_PTRS + 4 * i)),
        b00=b(e), b01=b(e + 1), b02=b(e + 2), b03=b(e + 3), b04=b(e + 4), b05=b(e + 5),
        counter=h(e + 6), f08=round(f(e + 8), 3), f0c=round(f(e + 0xC), 3), f10=round(f(e + 0x10), 3),
        h14=h(e + 0x14), h18=h(e + 0x18), h1c=h(e + 0x1C), b20=b(e + 0x20), code_chk=b(e + 0x21),
        raw=r[(e & 0xFFFFFF):(e & 0xFFFFFF) + STRIDE].hex()))
if len(sys.argv) > 2:
    json.dump(rows, open(sys.argv[2], "w"), indent=1)
print(f"{'no':>3} {'code':>4} {'name':20s} b0 b1 b2 b3 b4 b5 counter  f08     f0c     f10   b20 chk")
for x in rows:
    print(f"{x['no']:3d} {x['code']:#04x} {x['name']:20s} {x['b00']:2d} {x['b01']:2d} {x['b02']:2d} {x['b03']:2d} {x['b04']:2d} {x['b05']:2d} {x['counter']:6d} "
          f"{x['f08']:7.1f} {x['f0c']:7.1f} {x['f10']:7.1f} {x['b20']:3d} {x['code_chk']:#04x}")
