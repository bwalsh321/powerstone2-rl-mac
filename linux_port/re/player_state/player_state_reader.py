"""Ready-to-paste per-player / match-global reader for Power Stone 2 (guest RAM).
Compatible with ps2_ram.PS2Ram (uses only .u8/.u32/.f32). No repo file is modified.

Player struct P_k = 0x8C532498 + k*0x3938  (== PLAYER_MAT[k] - 0x490 == HEALTH_OBJ[k] - 0x160;
the code literal pools hard-code 0x0C532498, the P1 base).  See PLAYER_STATE.md for evidence.

Round 2 (Oct 4): collision-record list decoded. Records of 0x20 bytes start at P+0x184:
record 0 = the HURT cylinder, records 1..n-1 = live melee HIT spheres, n = byte3 of P+0x184.
Validated on all 14 selectable characters (precision 1.000, recall 0.978 vs an idle dummy) and in
4-player COM fights (pole swings, Power specials) - see out_e18b_multisphere.txt / out_e19b / out_e21*.
"""
import math

P_BASE = 0x8C532498
P_STRIDE = 0x3938

# ---- per-player offsets (from P_k) -------------------------------------
OFF_SEAT = 0x0001        # u8   seat index 0..3                                   CONFIRMED
OFF_CHAR = 0x0002        # u8   character id (CHAR_NAMES)                          CONFIRMED (all 14)
OFF_POS = 0x0028         # f32x3 logical world position x,y,z (y=0 on floor)      CONFIRMED
OFF_FACE = 0x0038        # u16  facing binary angle; forward = (sin a, cos a) in (x,z)  CONFIRMED
OFF_VEL = 0x004C         # f32x3 physics velocity, units/frame                    CONFIRMED (caveats in md)
OFF_ACC = 0x0058         # f32x3 acceleration (y = -1.2 gravity when airborne)    CONFIRMED
OFF_ATKFLAG = 0x0124     # u32  byte1 != 0 while attacking; ALSO set on thrown/getting-up bodies
                         #      with no hit sphere -> prefer hit_spheres() for "hitbox live"
OFF_HURTMASK = 0x012C    # u32  low u16 == 0 -> cannot be hit (i-frames)          CONFIRMED
OFF_FLAGS134 = 0x0134    # u32  bit 0x400 set -> grounded                         CONFIRMED
OFF_HEALTH = 0x0160      # f32  health (== HEALTH_OBJ)                            CONFIRMED
OFF_COLL = 0x0184        # collision record list, stride 0x20; byte3 of the first word = record count
COLL_STRIDE = 0x20       # record: +0 hdr (hurt: 0x??ff0206 ; hit: bone<<16 | 1), +8 x, +0xC y, +0x10 z,
                         #         +0x14 radius, +0x18 half-height (hurt only)
MAX_HIT_SPHERES = 6      # 4 seen in practice (Power specials); records past P+0x204 never used
OFF_STATE = 0x3715       # u8   state byte (== PSTATE_OFF from PLAYER_MAT)         CONFIRMED
OFF_PREV_STATE = 0x3716  # u8   previous state byte                                CONFIRMED
OFF_COM = 0x3720         # u8   1 = COM-controlled, 0 = human                      CONFIRMED
OFF_PARTNER = 0x3770     # u32  humans: grab partner (only set in grab/hold states 0(holding),11,12,33,34)
                         #      COMs: also the AI's current target player          CONFIRMED (grab) / LIKELY (COM target)
OFF_LAST_ATTACKER = 0x3774  # u32 struct ptr of the last MELEE attacker            CONFIRMED (166/166 melee hits)
OFF_ACT = 0x3818         # u16  action / animation id                              CONFIRMED
OFF_STUN = 0x3822        # u16  hit-stun timer (== PSTUN_OFF from PLAYER_MAT)      (known)

# ---- match globals -----------------------------------------------------
G_FIGHT_FRAMES = 0x8C475200   # u32 +1 per frame ONLY while the fight is live          CONFIRMED
G_MENU_OPEN = 0x8C46E1BB      # u8  1 while the pause menu or the continue menu is up  LIKELY
G_SEAT_TABLE = 0x8C472DA8     # 4 x 0x14: +0 type (0 human,1 COM,2 empty), +8 char id, +0x10 present  CONFIRMED
G_STAGE_AREA = 0x8C472CF8     # u32 stage area: 0 ship, 1 garden/castle, 3 iceberg, 4 space station,
                              #     5 desert (shared by the Pharaoh-walker stage)        LIKELY (6 stages)
G_COM_LEVEL_SETTING = 0x8C472AD4  # u8 == lv-1 on slot2/slot3 but writing it changes NOTHING (pre-match or live):
                                  #    a settings copy, not the live difficulty. Do not rely on it.

CHAR_NAMES = {0: "Falcon", 1: "Ryoma", 2: "Wang-Tang", 3: "Jack", 4: "Gunrock", 5: "Galuda", 6: "Ayame",
              7: "Rouge", 8: "Pete", 9: "Gourmand", 10: "Julia", 11: "Accel", 14: "Mel", 15: "Pride"}

STATE_NAMES = {
    0: "idle", 1: "run", 2: "brake", 4: "jump_squat", 5: "airborne", 6: "landing",
    7: "attack", 8: "use_item_or_throw_object", 9: "grab_attempt", 10: "pick_up",
    11: "grab_lift", 12: "throw_player", 14: "knocked_down", 15: "getting_up",
    16: "hit_recovery_air", 19: "entry_pose", 25: "power_change", 26: "power_special",
    30: "air_catch_item?", 32: "hit_reel", 33: "pole_or_object_followthrough?",
    34: "held_by_opponent", 35: "pole_grab", 36: "item_guard?",
}


def player_base(k):
    return P_BASE + k * P_STRIDE


def hurt_cylinder(ram, k):
    """(cx, cy, cz, radius, half_height); cy = pos.y + half_height. Shrinks when down (h 30) / getting up (h 55)."""
    b = player_base(k) + OFF_COLL
    return tuple(ram.f32(b + o) for o in (0x8, 0xC, 0x10, 0x14, 0x18))


def hit_spheres(ram, k):
    """List of live melee hit spheres (x, y, z, r). Empty list == no hitbox live this frame."""
    b = player_base(k) + OFF_COLL
    n = (ram.u32(b) >> 24) - 1
    out = []
    for j in range(1, 1 + max(0, min(n, MAX_HIT_SPHERES))):
        r = b + j * COLL_STRIDE
        out.append((ram.f32(r + 0x8), ram.f32(r + 0xC), ram.f32(r + 0x10), ram.f32(r + 0x14)))
    return out


def hit_contact(spheres, cyl):
    """The game's test (reproduced): horizontal dist <= r + R and |dy| <= r + H, for any sphere."""
    cx, cy, cz, R, H = cyl
    return any(math.hypot(x - cx, z - cz) <= r + R and abs(y - cy) <= r + H for x, y, z, r in spheres)


def threat_features(ram, me, opp):
    """Opponent opp's live hitbox relative to seat me: (dx, dy, dz, radius, margin) of the sphere
    nearest my hurt cylinder, or None. margin <= 0 means contact this frame (if I am hittable)."""
    sph = hit_spheres(ram, opp)
    if not sph:
        return None
    cx, cy, cz, R, H = hurt_cylinder(ram, me)
    best = None
    for x, y, z, r in sph:
        m = max(math.hypot(x - cx, z - cz) - (r + R), abs(y - cy) - (r + H))
        if best is None or m < best[4]:
            best = (x - cx, y - cy, z - cz, r, m)
    return best


def read_player(ram, k):
    """ram: ps2_ram.PS2Ram. Returns a dict of decoded fields for seat k (0..3)."""
    b = player_base(k)
    ang = ram.u32(b + OFF_FACE) & 0xFFFF
    th = ang * (2.0 * math.pi / 65536.0)
    st = ram.u8(b + OFF_STATE)
    sph = hit_spheres(ram, k)
    return {
        "char": ram.u8(b + OFF_CHAR),
        "com": ram.u8(b + OFF_COM),
        "pos": tuple(ram.f32(b + OFF_POS + 4 * i) for i in range(3)),
        "vel": tuple(ram.f32(b + OFF_VEL + 4 * i) for i in range(3)),
        "facing": (math.sin(th), math.cos(th)),          # (x, z) unit forward
        "state": st, "state_name": STATE_NAMES.get(st, f"s{st}"),
        "prev_state": ram.u8(b + OFF_PREV_STATE),
        "act": ram.u32(b + OFF_ACT) & 0xFFFF,
        "airborne": (ram.u32(b + OFF_FLAGS134) & 0x400) == 0,
        "invuln": (ram.u32(b + OFF_HURTMASK) & 0xFFFF) == 0,
        "hitbox_live": len(sph) > 0,
        "hit_spheres": sph,
        "hurt": hurt_cylinder(ram, k),
        "stun": ram.u32(b + OFF_STUN - 2) >> 16,           # u16 at +0x3822
        "health": ram.f32(b + OFF_HEALTH),
        "partner": _seat_of(ram.u32(b + OFF_PARTNER)),
        "last_attacker": _seat_of(ram.u32(b + OFF_LAST_ATTACKER)),
    }


def _seat_of(ptr):
    p = (ptr & 0x1FFFFFFF) | 0x80000000
    d = p - P_BASE
    if ptr and d >= 0 and d % P_STRIDE == 0 and d // P_STRIDE < 4:
        return d // P_STRIDE
    return -1


class HitboxClock:
    """Frames each seat's hitbox has been live (0 when none). Call once per env step with frames elapsed."""
    def __init__(self):
        self.age = [0, 0, 0, 0]

    def update(self, ram, frames=1):
        for k in range(4):
            self.age[k] = self.age[k] + frames if hit_spheres(ram, k) else 0
        return list(self.age)


class FightClock:
    """Live-fight detector: G_FIGHT_FRAMES advanced since the previous poll."""
    def __init__(self):
        self.prev = None

    def live(self, ram):
        v = ram.u32(G_FIGHT_FRAMES)
        out = self.prev is not None and v != self.prev
        self.prev = v
        return out
