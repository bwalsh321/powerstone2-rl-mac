"""Search a RAM dump for a per-item property table: entry[i] at base+i*stride
holding the observed initial counters: Gun(0)=6, Hammer(3)=600, PowerSword(5)=600,
SmallBomb(7)=420, MachineGun(0xb)=25, IceRod(0x38)=5, SoapBubbleGun(0x20)=250."""
import numpy as np, sys
r = np.frombuffer(open(sys.argv[1] if len(sys.argv) > 1 else "ram_slot2_f2000.bin", "rb").read(), np.uint8)
want = {0: 6, 3: 600, 5: 600, 7: 420, 0xb: 25, 0x38: 5, 0x20: 250}
for width, dt in ((2, "<u2"), (4, "<u4"), (1, "u1")):
    for stride in range(width, 257, width if width > 1 else 1):
        for align in range(0, stride, width):
            if width == 1 and max(want.values()) > 255:
                continue
            a = r[align: align + (len(r) - align) // stride * stride].reshape(-1, stride)[:, :width]
            v = a.copy().view(dt).ravel() if width > 1 else a.ravel()
            m = np.ones(len(v) - 0x40, bool)
            for i, val in want.items():
                m &= v[i:i + len(m)] == val
            for k in np.nonzero(m)[0]:
                print(f"HIT width={width} stride={stride:#x} base={0x0C000000 + align + k*stride:#x}")
# floats
f = r[: len(r)//4*4].view("<f4")
for stride in range(4, 257, 4):
    for align in range(0, stride, 4):
        v = f[align//4::stride//4]
        m = np.ones(len(v) - 0x40, bool)
        for i, val in want.items():
            m &= v[i:i+len(m)] == val
        for k in np.nonzero(m)[0]:
            print(f"HIT float stride={stride:#x} base={0x0C000000 + align + k*stride:#x}")
print("done")
