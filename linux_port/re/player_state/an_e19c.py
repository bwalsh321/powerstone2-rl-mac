"""Partner ptr P+0x3770, last-attacker P+0x3774, hurt-cylinder geometry checks (E19 data)."""
import collections, sys
import numpy as np
P0 = 0x0C532498; S = 0x3938
def seat(p):
    d = int(p) - P0
    return d // S if p and d >= 0 and d % S == 0 and d // S < 4 else -1
for tag in sys.argv[1:]:
    Z = np.load(f"data_e19_{tag}.npz"); out = Z["out"]; cols = list(Z["cols"]); raw = Z["raw"]
    c = {o: i for i, o in enumerate(cols)}
    U = lambda o: out[:, :, c[o]]; RF = lambda o: raw[:, :, (o - 0x160) // 4].view("<f4"); R = lambda o: raw[:, :, (o - 0x160) // 4]
    N = out.shape[0]; st = (U(0x3714) >> 8) & 0xFF; act = U(0x3818) & 0xFFFF
    part = np.vectorize(seat)(U(0x3770)); latt = np.vectorize(seat)(U(0x3774))
    raw_part = U(0x3770)
    print(f"== {tag}")
    # partner symmetry
    sym = collections.Counter(); bystate = collections.Counter(); nonplayer = collections.Counter()
    for t in range(N):
        for k in range(4):
            p = part[t, k]
            if p >= 0:
                sym["symmetric" if part[t, p] == k else "asym"] += 1
                bystate[(int(st[t, k]), int(st[t, p]))] += 1
            elif raw_part[t, k]:
                nonplayer[int(st[t, k])] += 1
    print("  partner->player frames:", dict(sym), " (holder state, partner state) top:", bystate.most_common(10))
    print("  partner set to a NON-player object, by state:", nonplayer.most_common(8))
    held = (st == 34)
    print("  frames in state 34 (held) with partner = a player:", f"{(part[held] >= 0).mean():.3f}", "n", held.sum())
    lift = (st == 11) | (st == 12)
    print("  frames in state 11/12 (lift/throw) with partner = a player:", f"{(part[lift] >= 0).mean():.3f}", "n", lift.sum())
    # last attacker vs melee attribution
    nhit = np.clip((R(0x184) >> 24).astype(int) - 1, 0, 8)
    hx, hy, hz, rr, hh = RF(0x18C), RF(0x190), RF(0x194), RF(0x198), RF(0x19C)
    hp = out[:, :, c[0x160]].view("<f4")
    def overlap(k, v, t):
        for j in range(nhit[t, k]):
            x, y, z, r = RF(0x1AC+0x20*j)[t, k], RF(0x1B0+0x20*j)[t, k], RF(0x1B4+0x20*j)[t, k], RF(0x1B8+0x20*j)[t, k]
            if np.hypot(x-hx[t, v], z-hz[t, v]) <= r + rr[t, v] and abs(y-hy[t, v]) <= r + hh[t, v]: return True
        return False
    la = collections.Counter(); la_other = collections.Counter()
    for t in range(1, N - 3):
        for v in range(4):
            d = hp[t-1, v] - hp[t, v]
            if not (0.01 < d < 900): continue
            who = [k for k in range(4) if k != v and (overlap(k, v, t) or overlap(k, v, t-1))]
            vals = set(latt[t:t+3, v].tolist())
            if who: la["melee: last-att == attacker" if who[0] in vals else f"melee: last-att {sorted(vals)}"] += 1
            else: la_other["non-melee: last-att " + ("set to a player" if any(x >= 0 for x in vals) else "not a player")] += 1
    print("  last attacker on melee hits:", dict(la)); print("  last attacker on non-melee damage:", dict(la_other))
    posy = out[:, :, c[0x2C]].view("<f4")
    e = np.abs(hy - (posy + hh))
    print(f"  hurt centre y == pos.y + half-height: {(e < 0.5).mean():.3f};  hurt x/z == pos x/z: {((np.abs(RF(0x18C) - out[:,:,c[0x28]].view('<f4')) < 0.5) & (np.abs(RF(0x194) - out[:,:,c[0x30]].view('<f4')) < 0.5)).mean():.3f}")
    print("  (r, half-h) by state (top):")
    tab = collections.defaultdict(collections.Counter)
    for s_, r_, h_ in zip(st.ravel(), np.round(rr).ravel(), np.round(hh).ravel()): tab[int(s_)][(r_, h_)] += 1
    for s_ in sorted(tab): print(f"    s{s_}: {tab[s_].most_common(3)}")
