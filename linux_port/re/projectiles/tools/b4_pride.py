import numpy as np
from collections import Counter
from common import *
for L in "AD":
    d = load(L); pact, pcls, ppos, hp, hs, led, pos, st = d["pact"], d["pcls"], d["ppos"], d["hp"], d["hsrc"], d["ledger"], d["pos"], d["st"]
    pk = LINEUPS[L].index("Pride")
    cls_c = Counter(); fr = []
    for f in range(len(pact)):
        live = ((pact[f] & 0xFF) == 1) & (pcls[f] >= 0x0C7E0000) & (pcls[f] < 0x0C7F0000)
        if live.any():
            cls_c.update(pcls[f][live].tolist()); fr.append(f)
    print(L, "Pride seat", pk, "frames with 0x0C7Exxxx live:", len(fr), [hex(c) for c, _ in cls_c.most_common(8)])
    # hits during those frames
    fs = set(fr); src = Counter()
    for f in fr:
        for k in range(4):
            if 0.5 < hp[f-1, k] - hp[f, k] < 900:
                p = int(hs[f, k]); s = seat_of(p); i, r = lslot(p)
                src[("seat", LINEUPS[L][s]) if s is not None else (hex(int(u32(led[f, i], 8))) if i is not None and i < led.shape[1] else hex(p), int(u32(led[f,i],4))&0xff if i is not None and i < led.shape[1] else -1)] += 1
    print("   hits in those frames by source:", src.most_common(10))
    print("   Pride states seen in those frames:", Counter(st[fr, pk].tolist()).most_common(6))
