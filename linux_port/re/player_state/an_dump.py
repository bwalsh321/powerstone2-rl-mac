"""Dump words of a recorded region over selected frames: python an_dump.py npz key base lo hi frames..."""
import sys, numpy as np, struct
f, key, base, lo, hi = sys.argv[1], sys.argv[2], int(sys.argv[3], 16), int(sys.argv[4], 16), int(sys.argv[5], 16)
frames = [int(x) for x in sys.argv[6].split(",")]
D = np.load(f); a = D[key]
print("addr      " + " ".join(f"{t:>11d}" for t in frames))
for ad in range(lo, hi, 4):
    o = ad - base
    ws = [struct.unpack_from("<I", a[t], o)[0] for t in frames]
    if len(set(ws)) == 1 and ws[0] == 0: continue
    def fmt(w):
        fl = struct.unpack("<f", struct.pack("<I", w))[0]
        if 1e-4 < abs(fl) < 1e6: return f"{fl:11.4g}"
        return f"   {w:08x}"
    mark = "*" if len(set(ws)) > 1 else " "
    print(f"{ad:08X}{mark} " + " ".join(fmt(w) for w in ws))
