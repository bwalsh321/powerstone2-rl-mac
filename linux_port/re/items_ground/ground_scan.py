"""ground_scan.py — ready-to-paste ground-object scanner for PS2Ram.

Reads the game's object arena (the "object ledger", 0x430-byte records on a
fixed grid) and returns every PICKUP-category object (header low byte 9) with
its type id, state, holder and position. See GROUND.md for the evidence.

Drop-in usage with the existing reader (no other repo change needed):

    from ps2_ram import PS2Ram
    from ground_scan import scan_ground, nearest_ground
    objs = scan_ground(PS2Ram(ram))                    # list[GroundObj]
    near = nearest_ground(objs, bx, by, bz, n=4)       # free items only

All offsets are CONFIRMED unless noted (GROUND.md has the receipts).
"""
from collections import namedtuple

import numpy as np

# ---- arena geometry ------------------------------------------------------
OBJ_GRID_LO = 0x8C4FBD30      # == ps2_addr.OBJ_GRID_LO (grid idx 0)
OBJ_STRIDE = 0x430
OBJ_ARENA_N = 208             # idx 0..207; idx 208 (0x8C532430) is the arena
                              # manager (category list heads), NOT a record.
                              # ps2_addr.OBJ_GRID_N = 110 misses idx >= 110
                              # (6.5% of chest / 8.6% of stone sightings).
ARENA_HEADS = 0x8C532434      # u32 head[cat] = first record+4 of category cat
                              # (records chain via +0x10 next / +0x0C prev,
                              # both pointing at record+4)

# ---- record fields -------------------------------------------------------
HDR = 0x04        # u32: b0 = category (9 = pickups/interactables, 5 = fx,
                  #      7 = camera/scene?, 8 = player-attached, 2/1 = misc)
                  #      b1 = holder/last-holder seat 0..3, 0xFF = never held
                  #      b2 = per-class spawn index (cactus/pole/chest pads)
VT = 0x08         # u32 vtable = behaviour class (see VT_* below)
POS = (0x2C, 0x30, 0x34)   # world x, y, z (LOCAL hand offset while held!)
MAT_T = (0x98, 0x9C, 0xA0) # world-matrix translation (render copy)
TYPE = 0x420      # u8  type id: 1..121 = item (same numbering as the item
                  #     catalogue: 1 Gun, 4 Hammer, 5 Sword, 12 Machine Gun,
                  #     25 Umbrella, 70 Skateboard ...), 0xC1 power stone,
                  #     0xC2 treasure chest, 0xC3 desert barrel-cactus,
                  #     0xC8 desert tall saguaro
STATE = 0x421     # u8  0 spawning/popping, 1 respawning(stage props),
                  #     2 resting/free, 5 HELD, 6 thrown/in flight,
                  #     7 held+in use, 8/10 stage-prop thrown/flying,
                  #     9 chest opening, 11 dying/breaking
USES = 0x424      # u16 remaining uses/durability (Hammer 600, Flame Thrower
                  #     220 ...) — LIKELY
STONE_COLOR = 0x428   # u8 stone colour/index 0..6 (only for TYPE 0xC1)
CHEST_CONTENT = 0x42C # u8 chest content = TYPE of what will pop out
                      # (0xC1 = a power stone); valid from chest birth until
                      # ~28 f after the chest starts opening (STATE 9).

VT_ITEM = 0x0C0C9810      # generic weapon / item (most ids). NOT a falling
                          # chest: ps2_addr.CHEST_FALL_VT is a misnomer.
VT_ITEM_BOMB = 0x0C0CA928  # bombs (ids 8 Small, 9 Medium, 10 Large Bomb ...)
VT_ITEM_FOOD = 0x0C0CA5D8  # food (16 Apple, 17 Short Cake, 18 Meat, 83 ...)
VT_ITEM_RIDE = 0x0C0C9F50  # vehicles (70 Skateboard ...)
VT_STONE = 0x0C0CBCB0      # loose power stone (TYPE 0xC1)
VT_CHEST = 0x0C0CC7A8      # treasure chest (TYPE 0xC2), born at y = 50
VT_CACTUS = 0x0C0F1688     # desert barrel cactus (0xC3): pick up & throw,
                           # regrows at its home spot
VT_SAGUARO = 0x0C0F18D4    # desert tall saguaro (0xC8), fixed, y = 0
VT_HELPER = 0x0C0CACAC     # short-lived player-owned helper — ignore (GUESS)
VT_WEARABLE = 0x0C0CA114   # wearable/accessory ids (0x59+) born at (0,0,0) —
                           # never a ground object — ignore (LIKELY)
VT_BEEHIVE = 0x0C0CE6EC    # 78 Beehive
VT_POLE_GROWN = 0x0C0CEB94 # 54 Bamboo Shoot -> grows into a 0xC8 pole
_IGNORE_VTS = np.array([VT_HELPER, VT_WEARABLE], np.uint32)

# coarse categories for the observation (see GROUND.md "obs-v4")
CAT_NONE, CAT_STONE, CAT_CHEST, CAT_RANGED, CAT_MELEE, CAT_THROW, CAT_FOOD, \
    CAT_PROP, CAT_OTHER = range(9)
N_CAT = 9

_RANGED = {1, 2, 3, 12, 13, 28, 33, 34, 40, 41, 42, 51, 52, 56, 57, 58, 59, 60,
           61, 62, 66, 67}
_THROW = {8, 9, 10, 11, 35, 53, 54, 55, 64, 65, 73, 75, 76, 77, 78, 100, 107,
          114}
_FOOD = {16, 17, 18, 83, 84, 85, 86, 87, 88, 104}
_MELEE = {4, 5, 6, 7, 14, 15, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31,
          32, 37, 38, 39, 43, 44, 45, 46, 47, 48, 49, 50, 63, 68, 69, 101, 102,
          105, 106, 116}


def category(type_id):
    if type_id == 0xC1:
        return CAT_STONE
    if type_id == 0xC2:
        return CAT_CHEST
    if 0xC3 <= type_id <= 0xCF:
        return CAT_PROP          # stage objects: 0xC3 throwable prop (cactus,
                                 # crate, ...), 0xC8 pole, others = stage gear
    if type_id in _RANGED:
        return CAT_RANGED
    if type_id in _MELEE:
        return CAT_MELEE
    if type_id in _THROW:
        return CAT_THROW
    if type_id in _FOOD:
        return CAT_FOOD
    if 1 <= type_id <= 121:
        return CAT_OTHER
    return CAT_NONE


GroundObj = namedtuple("GroundObj", "idx addr vt tid state holder x y z content cat")

# Kept for reference / tests; the scan itself is vt-AGNOSTIC (any live
# category-9 record that is not a helper), classified by the TYPE byte, so
# other stages' props (vts 0x0C0E8AE4 crate, 0x0C0F0E08 crate, ...) and rare
# item classes are not silently dropped.
_PICKUP_VTS = np.array([VT_ITEM, VT_ITEM_BOMB, VT_ITEM_FOOD, VT_ITEM_RIDE,
                        VT_STONE, VT_CHEST, VT_CACTUS, VT_SAGUARO], np.uint32)


def scan_ground(r, include_held=False, include_fixed=False):
    """r: ps2_ram.PS2Ram. Returns list[GroundObj] for live category-9 records.
    include_held: also return held objects (STATE 5/7; their x,y,z is a
    hand-local offset, NOT world — use the holder's position instead).
    include_fixed: also return the 4 fixed saguaros (0xC8)."""
    g = lambda fo: r.grid_words(OBJ_GRID_LO, OBJ_STRIDE, OBJ_ARENA_N, fo)
    hdr = g(HDR)
    vt = g(VT)
    live = (((hdr & 0xFF) == 9) & (vt >= 0x0C000000) & (vt < 0x0C200000)
            & ~np.isin(vt, _IGNORE_VTS))
    if not live.any():
        return []
    blk = g(0x420)                      # type | state<<8 | ... (one read)
    tid = blk & 0xFF
    st = (blk >> 8) & 0xFF
    cont = g(CHEST_CONTENT) & 0xFF
    xs = r.grid_floats(OBJ_GRID_LO, OBJ_STRIDE, OBJ_ARENA_N, POS[0])
    ys = r.grid_floats(OBJ_GRID_LO, OBJ_STRIDE, OBJ_ARENA_N, POS[1])
    zs = r.grid_floats(OBJ_GRID_LO, OBJ_STRIDE, OBJ_ARENA_N, POS[2])
    out = []
    for k in np.nonzero(live)[0]:
        s = int(st[k]); t = int(tid[k]); v = int(vt[k])
        if not include_held and s in (5, 7):
            continue
        if not include_fixed and t == 0xC8:
            continue
        x, y, z = float(xs[k]), float(ys[k]), float(zs[k])
        if x == 0.0 and y == 0.0 and z == 0.0:
            continue
        if not (x == x and z == z and abs(x) < 1e5 and abs(z) < 1e5):
            continue
        if not (y == y and abs(y) < 1e5):
            y = 0.0
        out.append(GroundObj(int(k), OBJ_GRID_LO + int(k) * OBJ_STRIDE, v, t, s,
                             int((hdr[k] >> 8) & 0xFF), x, y, z,
                             int(cont[k]) if v == VT_CHEST else 0, category(t)))
    return out


def nearest_ground(objs, bx, by, bz, n=4, cats=None, max_d=None):
    """Nearest-first free objects (stones/chests/items/props) to (bx,by,bz)."""
    c = [o for o in objs if (cats is None or o.cat in cats)]
    c.sort(key=lambda o: (o.x - bx) ** 2 + (o.z - bz) ** 2)
    if max_d is not None:
        c = [o for o in c if ((o.x - bx) ** 2 + (o.z - bz) ** 2) ** 0.5 <= max_d]
    return c[:n]


def obs_v4_block(objs, bx, by, bz, n=4, pos_scale=1000.0):
    """Proposed obs-v4 'ground' block: n slots x (present, dx, dz, dy,
    one-hot category[N_CAT-1], chest_has_stone) — see GROUND.md."""
    near = nearest_ground([o for o in objs if o.cat != CAT_NONE], bx, by, bz, n)
    w = 4 + (N_CAT - 1) + 1
    v = np.zeros(n * w, np.float32)
    for i, o in enumerate(near):
        b = i * w
        v[b] = 1.0
        v[b + 1] = np.clip((o.x - bx) / pos_scale, -2, 2)
        v[b + 2] = np.clip((o.z - bz) / pos_scale, -2, 2)
        v[b + 3] = np.clip((o.y - by) / pos_scale, -2, 2)
        v[b + 4 + (o.cat - 1)] = 1.0
        v[b + 4 + (N_CAT - 1)] = 1.0 if (o.cat == CAT_CHEST and o.content == 0xC1) else 0.0
    return v


GEMS_F = (0x8C535BB0, 0x8C5394E8, 0x8C53CE20, 0x8C540758)   # == ps2_addr.GEMS[p][1]


def held_type(r, seat):
    """Type id (+0x420) of what seat 0..3 holds, 0 = empty hands.
    F+0x54 points at the held object's arena record + 4 (NOT a definition
    table); the pointer is in the 0x0C mirror, PS2Ram wants 0x8C."""
    ptr = r.u32(GEMS_F[seat] + 0x54)
    if not (0x0C4FBD30 <= ptr < 0x0C532430):
        return 0
    return r.u8((ptr | 0x80000000) + 0x41C)
