import numpy as np, os
LINEUPS = {"A": ["Pride", "Falcon", "Ryoma", "Accel"], "B": ["Wang-Tang", "Galuda", "Rouge", "Jack"],
           "C": ["Pete", "Julia", "Gourmand", "Mel"], "D": ["Ayame", "Gunrock", "Falcon", "Pride"],
           "E": ["Pride", "Rouge", "Pete", "Wang-Tang"], "F": ["Julia", "Pride", "Rouge", "Galuda"]}
LEDGER_LO_P = 0x0C4FBD30; LSTRIDE = 0x430
PMAT = [0x8C532928, 0x8C536260, 0x8C539B98, 0x8C53D4D0]
PBASE = [(p - 0x490) & 0x0FFFFFFF for p in PMAT]
OBJ_LEN = 0x3938
HERE = os.path.dirname(os.path.abspath(__file__))
def load(L):
    d = dict(np.load(f"{HERE}/../cap/{L}/cap.npz"))
    d["ledger"] = np.load(f"{HERE}/../cap/{L}/ledger.npz")["ledger"]
    return d
def seat_of(phys):
    phys &= 0x0FFFFFFF
    for k in range(4):
        if PBASE[k] <= phys < PBASE[k] + OBJ_LEN: return k
    return None
def lslot(phys):
    phys &= 0x0FFFFFFF
    o = phys - LEDGER_LO_P
    if o < 0: return None, None
    return o // LSTRIDE, o % LSTRIDE
def u32(arr, off):   # arr [..., bytes] u8
    return (arr[..., off].astype(np.uint32) | arr[..., off+1].astype(np.uint32) << 8 |
            arr[..., off+2].astype(np.uint32) << 16 | arr[..., off+3].astype(np.uint32) << 24)
def f32(arr, off):
    return u32(arr, off).view(np.float32)
def owner_chain(led_f, i, hops=4):
    """Follow +0x14 from ledger slot i (frame snapshot led_f [NL,LB]) until a player object. Returns (seat|None, path)."""
    path = []
    for _ in range(hops):
        p = int(u32(led_f[i], 0x14)) & 0x0FFFFFFF
        s = seat_of(p)
        if s is not None: return s, path
        k, r = lslot(p)
        if p == 0 or k is None or k >= led_f.shape[0] or r != 4: return None, path + [hex(p)]
        path.append(hex(int(u32(led_f[k], 8)))); i = k
    return None, path
