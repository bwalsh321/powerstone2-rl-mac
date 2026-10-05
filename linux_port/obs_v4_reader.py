"""obs_v4_reader.py -- PROPOSED obs-v4 appended block for the Power Stone 2 bot (Oct 4 2026). Not wired in.

One module, numpy only, no repo imports. Given the SYSTEM_RAM view (or a ps2_ram.PS2Ram), the agent seat
and the opponent ordering the env already uses for the v2 opponent block (nearest-first, alive only), it
returns the APPENDED feature vector (V4_EXTRA = 270 dims, which go at obs[160:430]) plus a dict of decoded
values for debugging. The v3 prefix obs[0:160] is NOT produced here and must stay byte-identical (see
OBS_V4_SPEC.md for why, and for the [12..17] item-embedding recommendation).

    rdr = ObsV4Reader(ram)                          # one per emulator (shared by every seat's view)
    vec, info = rdr.features(seat, opp_order, frame)   # seat 0-based (learner = 1), opp_order = seat list

Seat-generic: the expensive, seat-independent part (player structs, the 208-slot object ledger) is read
ONCE per emulator frame and cached; each seat's view only does the cheap relative geometry. That is what
FFASelfPlayEnv._obs_from_view needs (4 views per env step on one emulator).

Sources (vendored, not imported, so the obs contract cannot drift when those RE files change):
  * re/player_state/player_state_reader.py + PLAYER_STATE.md   player struct P_k = 0x8C532498 + k*0x3938,
    collision records P+0x184 (hurt cylinder + live hit spheres), state/act/stun, flags, COM, partner.
  * re/projectiles/proposed_ledger_threats.py + PROJECTILES.md + RECONCILE.md   ledger category-1 hit
    volumes (lineup-independent), owner chain +0x14, velocity +0x50, radius +0x19C; P+0x414 startup ptr.
  * re/items_ground/ground_scan.py + GROUND.md   ledger grid 0x8C4FBD30, 208 slots, type +0x420,
    state +0x421, uses +0x424, chest content +0x42C, holder seat hdr byte 1.
  * re/items_held/items_dict.py + ITEMS.md   held type = record(F+0x54 - 4) + 0x420, game item table
    (initial counter, category), 5-way threat class.
  * ffa_selfplay_env._hit_attacker   last-hit-source attribution (P+0x3774 == PLAYER_MAT+0x32E4).
  * re/stage_geometry/stage_geom.py + STAGE.md (vendored as ./stage_geom.py): the 27-dim spatial block (free run
    along the 8 dpad directions vs the box + live props, nearest pole/cluster/wall, floor channels, map flag).
"""
import math
import struct

import numpy as np

import stage_geom as SG          # vendored from re/stage_geometry (see header there)

# ------------------------------------------------------------------ RAM geometry
RAM_BASE = 0x8C000000

P_BASE, P_STRIDE = 0x8C532498, 0x3938          # player struct (PLAYER_MAT - 0x490)        CONFIRMED
P_PHYS = [(P_BASE + k * P_STRIDE) & 0x0FFFFFFF for k in range(4)]
# player-struct offsets (PLAYER_STATE.md section 1)
OFF_CHAR = 0x0002            # u8 character id                                   CONFIRMED
OFF_POS = 0x0028             # f32x3 logical position (y = 0 on the floor)       CONFIRMED
OFF_VEL = 0x004C             # f32x3 velocity u/frame (vy exact in the air)      CONFIRMED (vy)
OFF_ATK124 = 0x0125          # u8 = byte1 of P+0x124: body/melee hitbox flag     CONFIRMED (41/41, RECONCILE)
OFF_HURTMASK = 0x012C        # u16 low half; 0 = cannot be hit                   CONFIRMED
OFF_FLAGS134_B1 = 0x0135     # u8 byte1 of P+0x134; bit 0x04 (= 0x400) grounded  CONFIRMED (byte read, RECONCILE)
OFF_COLL = 0x0184            # collision records, stride 0x20; count = u8 P+0x187 CONFIRMED
OFF_ATK414 = 0x0414          # u32 attack-descriptor ptr (startup warning)       CONFIRMED-ish (41/41, lead 9f)
OFF_STATE = 0x3715           # u8 state byte                                     CONFIRMED
OFF_COM = 0x3720             # u8 1 = COM                                        CONFIRMED
OFF_HELDPTR = 0x376C         # u32 F+0x54 = held record + 4                      CONFIRMED
OFF_PARTNER = 0x3770         # u32 grab partner / COM target                     CONFIRMED / LIKELY
OFF_LASTHIT = 0x3774         # u32 last hit source (== PLAYER_MAT+0x32E4)        CONFIRMED
OFF_STUN = 0x3822            # u16 hit-stun                                      (known, v3)
MAX_SPHERES = 6

LEDGER_LO, LEDGER_STRIDE, LEDGER_N = 0x8C4FBD30, 0x430, 208   # 208 CONFIRMED (GROUND.md; projectiles used 150)
G_FIGHT_FRAMES = 0x8C475200  # u32, +1/frame only while the fight is live       CONFIRMED
G_MENU_OPEN = 0x8C46E1BB     # u8 1 while a menu overlay is up                   LIKELY
G_STAGE = 0x8C46E198         # u32 stage id: 0 Blue sky 1 Dark castle 2 Tomb 3 Iceberg 4 Space station 5 Desert
                             #     6 Chaos (Pharaoh walker reads 5)                CONFIRMED (stage_geometry, 9 states)
G_VARIANT = 0x8C54235E       # u8 0 normal, 1 Pharaoh walker, 2 Chaos             CONFIRMED (stage_geometry)

# ledger categories / classes
CAT_HIT, CAT_MOVER2, CAT_STAGE = 1, 2, 9
CAT2_MOVERS = (0x0C16DBD4,)
# Ledger header byte 1 (+0x05) = OWNER SEAT of a category-1 hit volume (0xFF = none). Measured Oct 4 (re/obs_v4,
# test_obs_v4 part "owner"): equals the +0x14 parent-chain owner on 291/291 chain-owned volumes, and equals the seat
# whose held gun/rod counter ticked (fire event) on 111/114 item bullets, which have NO parent chain. It also names
# Pete's toy soldiers (unowned by chain). Same byte as GROUND.md's "holder seat" for category 9.
# Own volumes are dropped from the threat list EXCEPT blasts that can plausibly hurt the owner too (not ruled out):
SELF_HARM_VT = (0x0C163144, 0x0C162FD0)          # item blast, item explosion (bombs)
VT_HELPER, VT_WEARABLE = 0x0C0CACAC, 0x0C0CA114
T_STONE, T_CHEST = 0xC1, 0xC2

# ------------------------------------------------------------------ item classes (vendored from items_dict.ITEMS)
# code -> (held class, ground class, initial counter or 0 when the counter is not a resource)
#   held  : 0 MELEE (melee/shield), 1 RANGED_LONG, 2 RANGED_SHORT, 3 THROWN (thrown-on-use), 4 OTHER
#   ground: 0 MELEE, 1 RANGED, 2 THROWN, 3 FOOD, 4 OTHER
ITEM_CLS = {
    0x01: (1, 1, 6), 0x02: (1, 1, 5), 0x03: (2, 1, 220), 0x04: (0, 0, 600), 0x05: (0, 0, 600), 0x06: (0, 0, 600),
    0x07: (0, 0, 600), 0x08: (3, 2, 420), 0x09: (3, 2, 420), 0x0A: (3, 2, 420), 0x0B: (3, 2, 0), 0x0C: (1, 1, 25),
    0x0D: (1, 1, 5), 0x0E: (0, 0, 420), 0x0F: (0, 0, 420), 0x10: (4, 3, 0), 0x11: (4, 3, 0), 0x12: (4, 3, 0),
    0x13: (0, 0, 600), 0x14: (0, 0, 480), 0x15: (0, 0, 480), 0x16: (0, 0, 600), 0x17: (0, 0, 420), 0x18: (0, 0, 600),
    0x19: (0, 0, 600), 0x1A: (0, 0, 660), 0x1B: (0, 0, 480), 0x1C: (1, 1, 5), 0x1D: (0, 0, 600), 0x1E: (0, 0, 600),
    0x1F: (0, 0, 420), 0x20: (0, 0, 480), 0x21: (2, 1, 250), 0x22: (1, 1, 5), 0x23: (3, 2, 0), 0x24: (3, 2, 0),
    0x25: (0, 0, 480), 0x26: (0, 0, 420), 0x27: (0, 0, 420), 0x28: (1, 1, 8), 0x29: (1, 1, 4), 0x2A: (1, 1, 8),
    0x2B: (0, 0, 600), 0x2C: (0, 0, 600), 0x2D: (0, 0, 600), 0x2E: (0, 0, 480), 0x2F: (0, 0, 600), 0x30: (0, 0, 480),
    0x31: (0, 0, 480), 0x32: (0, 0, 420), 0x33: (1, 1, 7), 0x34: (1, 1, 5), 0x35: (3, 2, 0), 0x36: (3, 2, 0),
    0x37: (3, 2, 0), 0x38: (1, 1, 5), 0x39: (1, 1, 5), 0x3A: (1, 1, 5), 0x3B: (1, 1, 5), 0x3C: (1, 1, 5),
    0x3D: (1, 1, 5), 0x3E: (2, 1, 4), 0x3F: (0, 0, 420), 0x40: (3, 2, 0), 0x41: (3, 2, 0), 0x42: (2, 1, 5),
    0x43: (2, 1, 5), 0x44: (0, 0, 420), 0x45: (0, 0, 600), 0x46: (4, 4, 600), 0x47: (4, 4, 600), 0x48: (4, 4, 600),
    0x49: (3, 2, 0), 0x4A: (4, 4, 600), 0x4B: (1, 1, 10), 0x4C: (2, 1, 10), 0x4D: (1, 1, 10), 0x4E: (3, 2, 0),
    0x4F: (4, 4, 400), 0x50: (4, 4, 400), 0x51: (4, 4, 400), 0x52: (4, 4, 480), 0x53: (4, 3, 0), 0x54: (4, 3, 0),
    0x55: (4, 3, 0), 0x56: (4, 3, 0), 0x57: (4, 3, 0), 0x58: (4, 3, 0), 0x59: (4, 4, 0), 0x5A: (4, 4, 0),
    0x5B: (4, 4, 0), 0x5C: (4, 4, 0), 0x5D: (4, 4, 0), 0x5E: (4, 4, 0), 0x5F: (4, 4, 0), 0x60: (4, 4, 0),
    0x61: (4, 4, 0), 0x62: (4, 4, 0), 0x63: (4, 4, 0), 0x64: (3, 2, 0), 0x65: (0, 0, 420), 0x66: (0, 0, 600),
    0x67: (4, 4, 0), 0x68: (4, 3, 0), 0x69: (0, 0, 600), 0x6A: (0, 0, 600), 0x6B: (3, 2, 420), 0x6C: (4, 4, 0),
    0x6D: (4, 4, 0), 0x6E: (4, 4, 0), 0x6F: (4, 4, 0), 0x70: (4, 4, 0), 0x71: (4, 4, 0), 0x72: (3, 2, 0),
    0x73: (3, 2, 0), 0x74: (1, 1, 3), 0x75: (4, 4, 0), 0x76: (4, 4, 0), 0x77: (4, 4, 0),
}
# character ids (PLAYER_STATE.md, all 14 CONFIRMED) -> one-hot index
CHAR_IDS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15)
CHAR_NAMES = ("Falcon", "Ryoma", "Wang-Tang", "Jack", "Gunrock", "Galuda", "Ayame", "Rouge", "Pete", "Gourmand",
              "Julia", "Accel", "Mel", "Pride")
CHAR_IDX = {c: i for i, c in enumerate(CHAR_IDS)}

# ------------------------------------------------------------------ layout of the appended block
POS_SCALE, HEIGHT_SCALE = 1000.0, 500.0        # same scales as powerstone_env_v6 (stones/chests/projectiles)
MELEE_SCALE, THREAT_VSCALE = 300.0, 2400.0
N_OPP, N_THREAT, N_ITEM, N_CHEST = 3, 3, 3, 2

A_OPP_W = 11                    # per-opponent width of block A
A_MELEE, A_LEN = 0, 37          # 3 opp x 11 + self 4
B_THREAT, B_LEN = 37, 34        # 3 threats x 11 + crowd
C_GROUND, C_LEN = 71, 44        # 3 items x 10 + prop 4 + 2 chests x 5
D_HELD, D_LEN = 115, 24         # 4 seats (self, opp0..2) x 6
E_STATE, E_LEN = 139, 38        # 4 seats x 8 + 3 opp x 2
F_CHAR, F_LEN = 177, 56         # 4 seats x 14
G_GLOBAL, G_LEN = 233, 10       # fight_live, menu_open, stage one-hot 7, variant
H_SPATIAL, H_LEN = 243, 27      # stage geometry (stage_geom.SpatialEncoder, SPATIAL_DIM = 27)
V4_EXTRA = 270
V3_DIM = 160
V4_DIM = V3_DIM + V4_EXTRA      # 430

BLOCKS = {"A_melee": (A_MELEE, A_LEN), "B_threat": (B_THREAT, B_LEN), "C_ground": (C_GROUND, C_LEN),
          "D_held": (D_HELD, D_LEN), "E_state": (E_STATE, E_LEN), "F_char": (F_CHAR, F_LEN),
          "G_global": (G_GLOBAL, G_LEN), "H_spatial": (H_SPATIAL, H_LEN)}
assert sum(l for _, l in BLOCKS.values()) == V4_EXTRA


def feature_names():
    """Names for every appended dim (index i -> obs[160 + i])."""
    n = []
    for k in range(N_OPP):
        n += [f"A.opp{k}.{f}" for f in ("hit_live", "sph_dx", "sph_dy", "sph_dz", "sph_r", "margin", "hit_age",
                                         "atk414", "atk414_age", "body124", "item_swing")]
    n += ["A.self.hit_live", "A.self.best_margin", "A.self.atk414", "A.self.item_swing"]
    for t in range(N_THREAT):
        n += [f"B.thr{t}.{f}" for f in ("present", "dx", "dy", "dz", "vx", "vy", "vz", "radius", "thrown", "tca",
                                         "dca")]
    n += ["B.crowd600"]
    for i in range(N_ITEM):
        n += [f"C.item{i}.{f}" for f in ("present", "dx", "dz", "dy", "ready", "melee", "ranged", "thrown", "food",
                                          "other")]
    n += ["C.prop.present", "C.prop.dx", "C.prop.dz", "C.prop.big"]
    for i in range(N_CHEST):
        n += [f"C.chest{i}.{f}" for f in ("present", "dx", "dz", "dy", "has_stone")]
    for s in ("self", "opp0", "opp1", "opp2"):
        n += [f"D.{s}.{f}" for f in ("melee", "r_long", "r_short", "thrown", "other", "uses_frac")]
    for s in ("self", "opp0", "opp1", "opp2"):
        n += [f"E.{s}.{f}" for f in ("invuln", "airborne", "vy", "hurt_h", "down", "held", "grabbing", "state_age")]
    for k in range(N_OPP):
        n += [f"E.opp{k}.last_hit_me", f"E.opp{k}.com_targets_me"]
    for s in ("self", "opp0", "opp1", "opp2"):
        n += [f"F.{s}.{c}" for c in CHAR_NAMES]
    n += ["G.fight_live", "G.menu_open"] + [f"G.stage{i}" for i in range(7)] + ["G.variant"]
    n += [f"H.ray_{d}" for d in ("up", "down", "left", "right", "upleft", "upright", "downleft", "downright")]
    n += [f"H.{o}_{c}" for o in ("pole", "cluster", "wall") for c in ("right", "up", "dist")]
    n += ["H.height_above_floor"] + [f"H.floor_ahead_{d}" for d in ("up", "down", "left", "right", "upleft", "upright",
                                                                       "downleft", "downright")] + ["H.map_present"]
    assert len(n) == V4_EXTRA
    return n


# ------------------------------------------------------------------ helpers
def _as_ram(ram):
    r = getattr(ram, "ram", ram)            # PS2Ram -> ndarray
    if not isinstance(r, np.ndarray):
        r = np.frombuffer(r, np.uint8)
    return r


def _f32cols(block, off, n):
    """[rows, n] float32 from byte columns off..off+4n of a 2-D uint8 block (copy of a few bytes per row)."""
    return np.ascontiguousarray(block[:, off:off + 4 * n]).view("<f4").reshape(block.shape[0], n)


def _u32col(block, off):
    return np.ascontiguousarray(block[:, off:off + 4]).view("<u4").reshape(block.shape[0])


def _seat_of_phys(p):
    p &= 0x0FFFFFFF
    for k in range(4):
        if P_PHYS[k] <= p < P_PHYS[k] + P_STRIDE:
            return k
    return None


class ObsV4Reader:
    """Stateful only through per-seat onset clocks (hitbox / attack-window / state age) and the fight
    counter, all keyed by the emulator frame number passed in. Call order between seats never matters."""

    def __init__(self, ram, spatial_fn=None, spatial=True):
        self.ram = _as_ram(ram)
        self.spatial = spatial
        if spatial and getattr(self, "_sg", None) is None:
            self._sg = SG.SpatialEncoder()  # 0.7 s one-off precompute (Desert box map); other stages -> block = 0
        self._po = P_BASE - RAM_BASE
        self._lo = LEDGER_LO - RAM_BASE
        self.spatial_fn = spatial_fn        # optional: fn(ram, seat, frame) -> np.ndarray[<= H_LEN]
        self._frame = None
        self._cache = None
        self._calls = 0
        # onset clocks (frame when the condition started; None = off)
        self._hit_on = [None] * 4
        self._atk_on = [None] * 4
        self._atk_val = [0] * 4
        self._st_val = [None] * 4
        self._st_on = [0] * 4
        self._fight_prev = None
        self._fight_live = 0.0

    def reset(self):
        """Call after a loadstate (clocks restart)."""
        self.__init__(self.ram, self.spatial_fn, self.spatial)

    # -------------------------------------------------------------- per-frame shared scan
    def _scan(self, frame):
        r = self.ram
        PL = r[self._po:self._po + 4 * P_STRIDE].reshape(4, P_STRIDE)
        pos = _f32cols(PL, OFF_POS, 3).astype(np.float64)
        vel = _f32cols(PL, OFF_VEL, 3).astype(np.float64)
        cyl = _f32cols(PL, OFF_COLL + 8, 5).astype(np.float64)          # cx, cy, cz, R, H
        ncoll = PL[:, OFF_COLL + 3].astype(np.int64)
        raw = np.ascontiguousarray(PL[:, OFF_COLL + 0x20:OFF_COLL + 0x20 + 0x20 * MAX_SPHERES])
        coll = raw.view("<f4").reshape(4, MAX_SPHERES, 8)                # records 1..6: [hdr, ?, x, y, z, r, h, ?]
        chdr = raw.view("<u4").reshape(4, MAX_SPHERES, 8)[:, :, 0]
        st = PL[:, OFF_STATE].astype(np.int64)
        P = []
        for k in range(4):
            n = int(min(max(ncoll[k] - 1, 0), MAX_SPHERES))
            sph = np.zeros((0, 4))
            if n:
                # a live hit sphere has header (bone << 16) | 1 and r > 0. Records INSIDE the count can be empty
                # (header 0, r 0 at the origin: seen in Ryoma's power special, act 0x11b) -> filter them.
                c = coll[k, :n, 2:6].astype(np.float64)
                ok = ((chdr[k, :n] & 0xFFFF) == 1) & np.all(np.isfinite(c), axis=1) & (c[:, 3] > 0.0) & (c[:, 3] < 2000.0)
                sph = c[ok]
            atk = struct.unpack_from("<I", PL[k], OFF_ATK414)[0]
            P.append(dict(
                char=int(PL[k, OFF_CHAR]), pos=pos[k], vel=vel[k], cyl=cyl[k], spheres=sph, state=int(st[k]),
                body124=int(PL[k, OFF_ATK124]) != 0,
                invuln=(struct.unpack_from("<H", PL[k], OFF_HURTMASK)[0] == 0),
                airborne=(int(PL[k, OFF_FLAGS134_B1]) & 0x04) == 0,
                atk414=atk, com=int(PL[k, OFF_COM]),
                heldptr=struct.unpack_from("<I", PL[k], OFF_HELDPTR)[0],
                partner=struct.unpack_from("<I", PL[k], OFF_PARTNER)[0],
                lasthit=struct.unpack_from("<I", PL[k], OFF_LASTHIT)[0],
                stun=struct.unpack_from("<H", PL[k], OFF_STUN)[0]))
        # ---- held item per seat (record = F+0x54 - 4, a ledger slot)
        L = r[self._lo:self._lo + LEDGER_N * LEDGER_STRIDE].reshape(LEDGER_N, LEDGER_STRIDE)
        for k in range(4):
            p = P[k]
            p["held_code"], p["held_uses"], p["held_idx"] = 0, 0, None
            ptr = p["heldptr"]
            if ptr:
                o = ((ptr - 4) & 0x00FFFFFF) - self._lo          # 0x0C/0x8C mirrors -> RAM offset
                if 0 <= o < LEDGER_N * LEDGER_STRIDE and o % LEDGER_STRIDE == 0:
                    i = o // LEDGER_STRIDE
                    p["held_code"] = int(L[i, 0x420])
                    p["held_idx"] = int(i)
                    p["held_uses"] = int(L[i, 0x424]) | int(L[i, 0x425]) << 8
        # ---- held MELEE item swing: its own hit spheres live in the item's ledger record (not in the player list).
        # Record +0x188: list header (low u16 == 1, byte3 = count), spheres at +0x188 + 0x20*j: x,y,z,r at +8..+0x14.
        # Live while the holder swings (holder state 7/8, record state 7). Measured Oct 4 (OBS_V4_SPEC.md 5b): every
        # one of 22 item-melee hits (hit source = the held record) had margin <= 0 at the hit frame or the one before;
        # window level TP 19 / FP 5 / FN 0.
        for k in range(4):
            p = P[k]
            p["item_swing"] = False
            code = p["held_code"]
            if code in ITEM_CLS and ITEM_CLS[code][0] == 0 and p["held_idx"] is not None and p["state"] in (7, 8) \
                    and int(L[p["held_idx"], 0x421]) == 7:
                rec = L[p["held_idx"]]
                w = struct.unpack_from("<I", rec, 0x188)[0]
                if (w & 0xFFFF) == 1:
                    sl = []
                    for j in range(min(w >> 24, MAX_SPHERES)):
                        x, y, z, rad = struct.unpack_from("<4f", rec, 0x188 + 0x20 * j + 8)
                        if 0.0 < rad < 2000.0 and all(math.isfinite(q) for q in (x, y, z)):
                            sl.append((x, y, z, rad))
                    if sl:
                        p["item_swing"] = True
                        p["spheres"] = np.vstack([p["spheres"], np.array(sl)]) if len(p["spheres"]) else np.array(sl)

        # ---- clocks (advance once per distinct frame)
        for k in range(4):
            p = P[k]
            if len(p["spheres"]):
                if self._hit_on[k] is None:
                    self._hit_on[k] = frame
            else:
                self._hit_on[k] = None
            if p["atk414"]:
                if self._atk_on[k] is None or p["atk414"] != self._atk_val[k]:
                    self._atk_on[k] = frame
            else:
                self._atk_on[k] = None
            self._atk_val[k] = p["atk414"]
            if p["state"] != self._st_val[k]:
                self._st_val[k], self._st_on[k] = p["state"], frame
            # max(0, .): robust to a caller that passes a non-monotonic frame (pass ONE counter per emulator)
            p["hit_age"] = 0 if self._hit_on[k] is None else max(1, frame - self._hit_on[k] + 1)
            p["atk_age"] = 0 if self._atk_on[k] is None else max(1, frame - self._atk_on[k] + 1)
            p["state_age"] = max(0, frame - self._st_on[k])
        fc = struct.unpack_from("<I", r, G_FIGHT_FRAMES - RAM_BASE)[0]
        if self._fight_prev is not None and fc != self._fight_prev:
            self._fight_live = 1.0
        elif self._fight_prev is not None:
            self._fight_live = 0.0
        self._fight_prev = fc
        # ---- ledger (one vectorised pass over the 208 slots)
        cat = L[:, 4].astype(np.int64)
        holder = L[:, 5].astype(np.int64)
        vt = _u32col(L, 8)
        valid_vt = (vt >= 0x0C000000) & (vt < 0x0C200000)
        interesting = valid_vt & ((cat == CAT_HIT) | (cat == CAT_STAGE) | (cat == CAT_MOVER2))
        idx = np.nonzero(interesting)[0]
        led = None
        if len(idx):
            Li = L[idx]
            xyz = _f32cols(Li, 0x2C, 3).astype(np.float64)
            v = _f32cols(Li, 0x50, 3).astype(np.float64) * 60.0
            rad = _f32cols(Li, 0x19C, 1)[:, 0].astype(np.float64)
            led = dict(idx=idx, cat=cat[idx], holder=holder[idx], vt=vt[idx], xyz=xyz, vel=v, rad=rad,
                       tid=Li[:, 0x420].astype(np.int64), st=Li[:, 0x421].astype(np.int64),
                       content=Li[:, 0x42C].astype(np.int64), parent=_u32col(Li, 0x14))
        # threats (seat-independent part): category-1 hit volumes with owner; thrown category-9; cat-2 mover
        threats = []
        ground_items, props, chests = [], [], []
        stones = []                       # (x, y, z, ledger idx, state) of loose stones (overlay / debugging)
        sg_props = []                     # stage_geom.read_props equivalent: (vt, x, z, y) of every live pole/cluster
        if led is not None:
            for j in range(len(led["idx"])):
                c, vtj = int(led["cat"][j]), int(led["vt"][j])
                x, y, z = led["xyz"][j]
                vx, vy, vz = led["vel"][j]
                if not (math.isfinite(x) and math.isfinite(z) and abs(x) < 1e5 and abs(z) < 1e5):
                    continue
                if not (math.isfinite(y) and abs(y) < 1e5):
                    y = 0.0
                if not all(math.isfinite(q) and abs(q) < 1e5 for q in (vx, vy, vz)):
                    vx = vy = vz = 0.0
                rr = float(led["rad"][j])
                rr = rr if (math.isfinite(rr) and 0.0 < rr < 2000.0) else 0.0
                if c == CAT_HIT:
                    own = self._owner(int(led["idx"][j]), L)
                    if own is None and int(led["holder"][j]) < 4:
                        own = int(led["holder"][j])           # header byte 1 = owner seat (item bullets, summons)
                    threats.append((x, y, z, vx, vy, vz, rr, 0.0, own, vtj))
                    continue
                if c == CAT_MOVER2:
                    if vtj in CAT2_MOVERS and (vx * vx + vz * vz) ** 0.5 >= 300.0:
                        threats.append((x, y, z, vx, vy, vz, rr, 1.0, None, vtj))
                    continue
                # category 9: pickups / props / chests / thrown objects
                if vtj in SG.PROP_RADIUS:
                    sg_props.append((vtj, x, z, y))
                if vtj in (VT_HELPER, VT_WEARABLE):
                    continue
                s, t = int(led["st"][j]), int(led["tid"][j])
                if x == 0.0 and y == 0.0 and z == 0.0:
                    continue
                sp = (vx * vx + vy * vy + vz * vz) ** 0.5
                if t == T_STONE:                                   # loose power stone (own obs block in v2)
                    if s not in (10, 11):
                        stones.append((x, y, z, int(led["idx"][j]), s))
                    continue
                if s == 8 or (s == 6 and sp >= 600.0):           # thrown / tossed hard: a physical threat
                    if t != T_STONE:
                        hs = int(led["holder"][j])
                        threats.append((x, y, z, vx, vy, vz, 0.0, 1.0, hs if hs < 4 else None, vtj))
                    continue
                if s in (5, 7, 10, 11):                            # held / dying
                    continue
                if t == T_CHEST:
                    if s in (2, 9):
                        chests.append((x, y, z, 1.0 if int(led["content"][j]) == T_STONE else 0.0, int(led["content"][j]), s))
                elif 1 <= t <= 0x79:
                    if s in (0, 2, 6) and t in ITEM_CLS:
                        ground_items.append((x, y, z, 1.0 if s == 2 else 0.0, ITEM_CLS[t][1], t))
                elif 0xC3 <= t <= 0xCF:
                    if s == 2:
                        props.append((x, y, z, 1.0 if t == 0xC8 else 0.0, t))
        g_stage = struct.unpack_from("<I", r, G_STAGE - RAM_BASE)[0]
        menu = int(r[G_MENU_OPEN - RAM_BASE])
        variant = int(r[G_VARIANT - RAM_BASE])
        return dict(P=P, threats=threats, items=ground_items, props=props, chests=chests, stones=stones, sg_props=sg_props,
                    stage=g_stage, variant=variant, menu=menu, fight_live=self._fight_live, frame=frame)

    def _owner(self, slot, L, hops=4):
        """Follow ledger +0x14 (parent) to a player struct; None = unowned (vendored owner_seat)."""
        lo_phys = self._lo                                  # RAM offset of ledger slot 0
        for _ in range(hops):
            p = struct.unpack_from("<I", L[slot], 0x14)[0] & 0x0FFFFFFF
            s = _seat_of_phys(p)
            if s is not None:
                return s
            o = ((p - 4) & 0x00FFFFFF) - lo_phys
            if p == 0 or o < 0 or o % LEDGER_STRIDE or o // LEDGER_STRIDE >= LEDGER_N:
                return None
            slot = o // LEDGER_STRIDE
        return None

    def _hit_source(self, k):
        """Seat that last hit seat k (melee: P+0x3774 is a player struct; otherwise a ledger slot+4 -> owner)."""
        src = self._cache["P"][k]["lasthit"] & 0x0FFFFFFF
        if src == 0:
            return None
        s = _seat_of_phys(src)
        if s is not None:
            return None if s == k else s
        o = ((src - 4) & 0x00FFFFFF) - self._lo
        if o < 0 or o % LEDGER_STRIDE or o // LEDGER_STRIDE >= LEDGER_N:
            return None
        L = self.ram[self._lo:self._lo + LEDGER_N * LEDGER_STRIDE].reshape(LEDGER_N, LEDGER_STRIDE)
        s = self._owner(o // LEDGER_STRIDE, L)
        if s is None and int(L[o // LEDGER_STRIDE, 5]) < 4:
            s = int(L[o // LEDGER_STRIDE, 5])                 # header byte 1 = owner seat
        return None if (s is None or s == k) else s

    # -------------------------------------------------------------- public
    def scan(self, frame=None):
        """Seat-independent read, cached per frame. frame=None -> internal call counter (tests/tools)."""
        if frame is None:
            self._calls += 1
            frame = self._calls
        if frame != self._frame or self._cache is None:
            self.n_scans = getattr(self, "n_scans", 0) + 1
            self._cache = self._scan(frame)
            self._frame = frame
        return self._cache

    def features(self, seat, opp_order, frame=None):
        """seat: 0-based seat of the observer. opp_order: seats in the SAME order as the env's v2 opponent
        block (self._opps(s)[:3], nearest-first, alive only). Returns (np.float32[V4_EXTRA], info dict)."""
        S = self.scan(frame)
        P = S["P"]
        me = P[seat]
        opps = [int(j) for j in list(opp_order)[:N_OPP] if 0 <= int(j) < 4 and int(j) != seat]
        out = np.zeros(V4_EXTRA, np.float32)
        info = {"seat": seat, "opps": opps, "frame": S["frame"]}
        mx, my, mz = me["pos"]
        cx, cy, cz, R, H = me["cyl"]
        if not all(math.isfinite(q) for q in (cx, cy, cz, R, H)):
            cx, cy, cz, R, H = mx, my, mz, 0.0, 0.0

        # "absent" reads as "far": empty opponent slots get margin 1, empty threat slots get dca 2
        for k in range(N_OPP):
            out[A_MELEE + A_OPP_W * k + 5] = 1.0
        for t in range(N_THREAT):
            out[B_THREAT + 11 * t + 10] = 2.0

        # ---- A: melee threat (opponent hit spheres vs MY hurt cylinder) + attack windows
        info["melee"] = []
        for k, j in enumerate(opps):
            p, b = P[j], A_MELEE + A_OPP_W * k
            best = None
            for x, y, z, r in p["spheres"]:
                m = max(math.hypot(x - cx, z - cz) - (r + R), abs(y - cy) - (r + H))
                if best is None or m < best[4]:
                    best = (x - cx, y - cy, z - cz, r, m)
            if best is not None:
                out[b:b + 6] = (1.0, best[0] / MELEE_SCALE, best[1] / MELEE_SCALE, best[2] / MELEE_SCALE,
                                best[3] / 100.0, max(-1.0, min(1.0, best[4] / 200.0)))
                out[b + 6] = min(1.0, p["hit_age"] / 20.0)
            if p["atk414"]:
                out[b + 7] = 1.0
                out[b + 8] = min(1.0, p["atk_age"] / 30.0)
            out[b + 9] = 1.0 if p["body124"] else 0.0
            out[b + 10] = 1.0 if p["item_swing"] else 0.0         # spheres above include the swung item's blade
            info["melee"].append(dict(seat=j, spheres=len(p["spheres"]), best=best, atk414=p["atk414"],
                                      atk_age=p["atk_age"], hit_age=p["hit_age"]))
        b = A_MELEE + A_OPP_W * N_OPP
        mym = None
        for j in opps:
            ox, oy, oz, oR, oH = P[j]["cyl"]
            for x, y, z, r in me["spheres"]:
                m = max(math.hypot(x - ox, z - oz) - (r + oR), abs(y - oy) - (r + oH))
                mym = m if mym is None else min(mym, m)
        out[b] = 1.0 if len(me["spheres"]) else 0.0
        out[b + 1] = 1.0 if mym is None else max(-1.0, min(1.0, mym / 200.0))
        out[b + 2] = 1.0 if me["atk414"] else 0.0
        out[b + 3] = 1.0 if me["item_swing"] else 0.0

        # ---- B: ledger threats (not mine), nearest-first, with closest-approach
        thr = []
        for (x, y, z, vx, vy, vz, rr, thrown, owner, vtj) in S["threats"]:
            if owner == seat and vtj not in SELF_HARM_VT:
                continue
            dx, dy, dz = x - mx, y - my, z - mz
            if any(abs(dx - q[0]) < 5.0 and abs(dz - q[2]) < 5.0 for q in thr):
                continue                                           # one entry per position (multi-part objects)
            thr.append((dx, dy, dz, vx, vy, vz, rr, thrown, owner, vtj))
        thr.sort(key=lambda q: q[0] * q[0] + q[2] * q[2])
        info["threats"] = thr[:6]
        for t, (dx, dy, dz, vx, vy, vz, rr, thrown, owner, vtj) in enumerate(thr[:N_THREAT]):
            b = B_THREAT + 11 * t
            # closest approach (me static over the next second): t* = -p.v / |v|^2 in [0, 1 s]
            vv = vx * vx + vy * vy + vz * vz
            tca = 0.0 if vv < 1.0 else max(0.0, min(1.0, -(dx * vx + dy * vy + dz * vz) / vv))
            ex, ey, ez = dx + vx * tca, dy + vy * tca, dz + vz * tca
            dca = (ex * ex + ey * ey + ez * ez) ** 0.5
            out[b:b + 11] = (1.0, dx / POS_SCALE, dy / HEIGHT_SCALE, dz / POS_SCALE, vx / THREAT_VSCALE,
                             vy / THREAT_VSCALE, vz / THREAT_VSCALE, rr / 300.0, thrown, tca, min(2.0, dca / 500.0))
        out[B_THREAT + 33] = min(10, sum(1 for q in thr if q[0] * q[0] + q[2] * q[2] < 600.0 ** 2)) / 5.0

        # ---- C: ground items, nearest ready prop, chests with content
        it = sorted(S["items"], key=lambda q: (q[0] - mx) ** 2 + (q[2] - mz) ** 2)
        info["items"] = [(q[5], q[3], round(q[0] - mx), round(q[2] - mz)) for q in it[:N_ITEM]]
        for i, (x, y, z, ready, gcls, t) in enumerate(it[:N_ITEM]):
            b = C_GROUND + 10 * i
            out[b:b + 5] = (1.0, (x - mx) / POS_SCALE, (z - mz) / POS_SCALE, (y - my) / HEIGHT_SCALE, ready)
            out[b + 5 + gcls] = 1.0
        pr = sorted(S["props"], key=lambda q: (q[0] - mx) ** 2 + (q[2] - mz) ** 2)
        if pr:
            x, y, z, big, t = pr[0]
            b = C_GROUND + 30
            out[b:b + 4] = (1.0, (x - mx) / POS_SCALE, (z - mz) / POS_SCALE, big)
        ch = sorted(S["chests"], key=lambda q: (q[0] - mx) ** 2 + (q[2] - mz) ** 2)
        info["chests"] = [(round(q[0] - mx), round(q[2] - mz), q[3]) for q in ch[:N_CHEST]]
        for i, (x, y, z, stone, _content, _st) in enumerate(ch[:N_CHEST]):
            b = C_GROUND + 34 + 5 * i
            out[b:b + 5] = (1.0, (x - mx) / POS_SCALE, (z - mz) / POS_SCALE, (y - my) / HEIGHT_SCALE, stone)

        # ---- D/E/F: per-seat intrinsic blocks (self, opp0..2)
        seats = [seat] + opps
        info["held"], info["state"] = [], []
        for s_i, j in enumerate(seats):
            p = P[j]
            code = p["held_code"]
            b = D_HELD + 6 * s_i
            if code:
                if code in ITEM_CLS:
                    hc, _, init = ITEM_CLS[code]
                    frac = min(1.0, p["held_uses"] / init) if init else 1.0
                elif code >= 0xC3:
                    hc, frac = 3, 1.0                              # carried stage prop = a throw
                else:
                    hc, frac = 4, 1.0
                out[b + hc] = 1.0
                out[b + 5] = frac
            info["held"].append((j, code, p["held_uses"]))
            b = E_STATE + 8 * s_i
            stt = p["state"]
            hh = p["cyl"][4]
            out[b:b + 8] = (1.0 if p["invuln"] else 0.0, 1.0 if p["airborne"] else 0.0,
                            max(-2.0, min(2.0, p["vel"][1] / 30.0)) if math.isfinite(p["vel"][1]) else 0.0,
                            max(0.0, min(2.0, hh / 100.0)) if math.isfinite(hh) else 0.0,
                            1.0 if stt in (14, 15) else 0.0, 1.0 if stt == 34 else 0.0,
                            1.0 if stt in (9, 11, 12) else 0.0, min(1.0, p["state_age"] / 60.0))
            info["state"].append((j, stt, p["invuln"], p["airborne"], p["state_age"]))
            ci = CHAR_IDX.get(p["char"])
            if ci is not None:
                out[F_CHAR + 14 * s_i + ci] = 1.0
        my_phys = P_PHYS[seat]
        src = self._hit_source(seat)
        info["last_hit_by"] = src
        for k, j in enumerate(opps):
            b = E_STATE + 32 + 2 * k
            out[b] = 1.0 if src == j else 0.0
            pt = P[j]["partner"] & 0x0FFFFFFF
            out[b + 1] = 1.0 if (P[j]["com"] == 1 and my_phys <= pt < my_phys + P_STRIDE) else 0.0

        # ---- G: globals
        out[G_GLOBAL] = S["fight_live"]
        out[G_GLOBAL + 1] = 1.0 if S["menu"] == 1 else 0.0
        if 0 <= S["stage"] < 7:
            out[G_GLOBAL + 2 + S["stage"]] = 1.0
        out[G_GLOBAL + 9] = 1.0 if S["variant"] != 0 else 0.0
        info["stage"], info["variant"], info["fight_live"] = S["stage"], S["variant"], S["fight_live"]

        # ---- H: spatial block (stage_geom.SpatialEncoder at my LOGICAL position, live props from the shared scan)
        if self.spatial and self.spatial_fn is None:
            sv = self._sg(self.ram, float(mx), float(my), float(mz), props=S["sg_props"])
            out[H_SPATIAL:H_SPATIAL + H_LEN] = sv
            info["spatial"] = sv
        elif self.spatial_fn is not None:
            sv = np.asarray(self.spatial_fn(self.ram, seat, S["frame"]), np.float32).ravel()[:H_LEN]
            out[H_SPATIAL:H_SPATIAL + len(sv)] = sv

        np.clip(out, -5.0, 5.0, out=out)
        out[~np.isfinite(out)] = 0.0
        return out, info
