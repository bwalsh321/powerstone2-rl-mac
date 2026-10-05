"""PROPOSED (not wired in): ledger-based threat scanner for Power Stone 2 -- obs v4 candidate.

Drop-in companion to ps2_ram.py (does NOT edit it). Reads the game's own object ledger
(0x8C4FBD30, stride 0x430) instead of the render pool, because:

  * Pool class words (0x0C5xxxxx-0x0C8xxxxx) are MODEL-DATA addresses and SHIFT WITH THE LINEUP
    (Falcon's missile body = 0x0C7FABC8 in the slot3 lineup, 0x0C808BC8 with Ayame/Gunrock loaded;
    the v2 'rocket' 0x0C7F9A10 becomes 0x0C807A10). Any pool whitelist/exclude list is valid for ONE
    lineup only -- unusable on lv8mix mixed-arena states.
  * Ledger words at slot+0x08 are CODE addresses (behaviour vtables) and are lineup-independent
    (Falcon missile 0x0C122FEC in every lineup, every seat).

Ledger slot layout used (offsets from the slot base; base = 0x8C4FBD30 + k*0x430):
  +0x04 u32  header; LOW BYTE = list/category: 1 = live HIT VOLUME (every special/super/projectile,
             item bullets, explosions), 5 = effects, 7/8 = system, 9 = stage objects (items, chests,
             loose stones, throwable props), 0 = free
  +0x08 u32  behaviour vtable (class identity, lineup-independent)
  +0x0C/+0x10 list links (prev/next; ptr = slot+4)
  +0x14 u32  parent: a PLAYER OBJECT (PLAYER_MAT[k]-0x490 .. +0x3938) or another ledger object
             (follow it); 0 for items / some summons (no owner)
  +0x2C/+0x30/+0x34 f32  position x, y, z
  +0x50/+0x54/+0x58 f32  velocity, units PER FRAME (x60 = u/s) -- exact for every class tested
  +0x19C f32 hit radius candidate (10 missile, 50 Accel bullet, 180 boulder, 275 Ryoma pillar ...)
  +0x1BC f32 second extent candidate (30-190)
Player objects (PLAYER_MAT[k] - 0x490 base):
  +0x134 u8  melee move id while a melee attack window is open (0 otherwise)
  +0x414 u32 pointer to the move's 0x14-byte attack descriptor while the window is open
             (0 otherwise). 40/40 melee hits landed inside the attacker's window, at frame ~7.
  hit source PLAYER_MAT+0x32E4 (existing, HANDOFF Sep 29) points at ledger slot+4 for non-melee hits.

Usage: sc = LedgerThreatScanner(bot_seat=1); res = sc(ram, frame) -> dict(threats=[...], melee=[...]).
(scan() alone, without hist, reports category-1 hit volumes only -- thrown objects need history.)
"""
import struct
import numpy as np

RAM_BASE = 0x8C000000
LEDGER_LO = 0x8C4FBD30
LSTRIDE = 0x430
LEDGER_N = 150                       # live slots seen up to index ~130
PLAYER_MAT = [0x8C532928, 0x8C536260, 0x8C539B98, 0x8C53D4D0]
PBASE = [(p - 0x490) & 0x0FFFFFFF for p in PLAYER_MAT]
POBJ_LEN = 0x3938

CAT_HIT, CAT_STAGE = 1, 9
LOOSE_STONE_VT = 0x0C0CBCB0          # has its own obs channel
CHEST_REST_VT = 0x0C0CC7A8
ABSORB_ARC_VT = 0x0C0CACAC           # stone-absorb arc (ps2_addr OBJ_KNOWN_UNREPORTED)
STAGE_EXCLUDE = {LOOSE_STONE_VT, CHEST_REST_VT, ABSORB_ARC_VT}
CAT2_MOVERS = {0x0C16DBD4}           # category-2 ground mover (item); 0x0C14DBD0 / 0x0C0CB310 are static
THROWN_MIN_SPEED = 600.0             # u/s, 3-D  (fighters run ~360; held objects ride at fighter speed)
THROWN_MIN_HSPEED = 300.0            # u/s, horizontal (drops/falling chests are vertical)
HELD_RADIUS = 120.0                  # xz distance from a fighter's centre that counts as 'held'

# Optional labels (evidence: re/projectiles/PROJECTILES.md). Unknown vtables still get reported.
LABELS = {
    0x0C122FEC: "missile (Falcon PF swarm / Pride rocket swarm)", 0x0C12212C: "Falcon shot",
    0x0C12360C: "Pride", 0x0C14E224: "Pride",
    0x0C127448: "Ryoma sky pillar", 0x0C128112: "Ryoma big pillar (ownerless)",
    0x0C128A18: "Wang-Tang slash wave", 0x0C129C70: "Wang-Tang shot", 0x0C129FA2: "Wang-Tang",
    0x0C12B034: "Jack knives", 0x0C12C8D0: "Gunrock boulder", 0x0C12CF48: "Gunrock rocks",
    0x0C12DA56: "Gunrock shockwave", 0x0C12E7D0: "Galuda wing beam", 0x0C12FB0A: "Ayame shuriken",
    0x0C130640: "Ayame dash beam", 0x0C132D70: "Rouge", 0x0C1351CA: "Rouge", 0x0C1357EE: "Rouge",
    0x0C139010: "Pete toy soldiers", 0x0C13A36C: "Pete", 0x0C13A79E: "Pete", 0x0C13A990: "Pete",
    0x0C13AC58: "Pete", 0x0C137CB4: "Pete energy blade", 0x0C1392D8: "Pete",
    0x0C136AB4: "light pillar (Pete? lineup C only)", 0x0C136FF4: "light pillar (Pete? lineup C only)",
    0x0C13831C: "pink flyer (lineup C only)", 0x0C13B906: "Gourmand", 0x0C13D28A: "Gourmand",
    0x0C13D04C: "Gourmand", 0x0C13EACC: "Gourmand pot/pig", 0x0C140CC0: "Julia",
    0x0C143608: "Accel gatling bullet", 0x0C143118: "Accel beam", 0x0C14D830: "Mel",
    0x0C162DAC: "item gun bullet", 0x0C162FD0: "item explosion", 0x0C163144: "item blast",
    0x0C163514: "item flame", 0x0C1638B4: "item fire (ground)", 0x0C163F9E: "item",
    0x0C1682B0: "item ray shot", 0x0C16906C: "item hammer/swing", 0x0C16B9D2: "item",
    0x0C16BF02: "item",
    0x0C0F1688: "thrown prop (desert cactus)", 0x0C0F18D4: "big prop", 0x0C0C9810: "item / chest object",
}


def _u32(ram, o):
    return int(ram[o]) | int(ram[o + 1]) << 8 | int(ram[o + 2]) << 16 | int(ram[o + 3]) << 24


def _f32(ram, o):
    return struct.unpack_from("<f", ram, o)[0]


def _seat(phys):
    phys &= 0x0FFFFFFF
    for k in range(4):
        if PBASE[k] <= phys < PBASE[k] + POBJ_LEN:
            return k
    return None


def owner_seat(ram, slot_off, hops=4):
    """Follow +0x14 (parent) until a player object; None = unowned (items, some summons)."""
    lo = LEDGER_LO - RAM_BASE
    for _ in range(hops):
        p = _u32(ram, slot_off + 0x14) & 0x0FFFFFFF
        s = _seat(p)
        if s is not None:
            return s
        o = (p | 0x80000000) - RAM_BASE - 4          # ledger pointers address slot+4
        if p == 0 or o < lo or (o - lo) % LSTRIDE or (o - lo) // LSTRIDE >= LEDGER_N:
            return None
        slot_off = o
    return None


class LedgerThreatScanner:
    """Stateful wrapper: the thrown-object gate needs one previous sweep, because +0x50 velocity is
    NOT cleared when a prop respawns at its pad (stale velocity on a frozen object). Call every
    sweep with the emulator frame number; 3-frame cadence (STONE_SCAN_EVERY) is fine."""

    def __init__(self, bot_seat=1):
        self.bot_seat = bot_seat
        self.prev = {}            # slot -> (vt, x, z, frame)
        self.prev_pp = None       # (player_pos, frame)

    def __call__(self, ram, frame):
        pp = np.array([[_f32(ram, p - RAM_BASE + 0x30 + 4 * i) for i in range(3)] for p in PLAYER_MAT])
        pv = np.zeros((4, 3))
        if self.prev_pp is not None and 0 < frame - self.prev_pp[1] < 30:
            pv = (pp - self.prev_pp[0]) * 60.0 / (frame - self.prev_pp[1])
        self.prev_pp = (pp, frame)
        res = scan(ram, self.bot_seat, pp, player_vel=pv, hist=self.prev, frame=frame)
        return res


def scan(ram, bot_seat=1, player_pos=None, player_vel=None, hist=None, frame=0):
    """ram: SYSTEM_RAM uint8 view. bot_seat: 0-based (in-game P2 = 1).
    player_pos: optional [4,3] fighter positions (PLAYER_MAT+0x30); read from RAM when None.
    Returns {'threats': [dict], 'melee': [dict per seat]}; threats are NOT sorted (caller sorts by
    distance to the bot, as the v3 reader does)."""
    if player_pos is None:
        player_pos = np.array([[_f32(ram, p - RAM_BASE + 0x30 + 4 * i) for i in range(3)] for p in PLAYER_MAT])
    lo = LEDGER_LO - RAM_BASE
    out = []
    for k in range(LEDGER_N):
        o = lo + k * LSTRIDE
        cat = ram[o + 4]
        if cat not in (CAT_HIT, CAT_STAGE, 2):
            continue
        vt = _u32(ram, o + 8)
        if not (0x0C000000 <= vt < 0x0C200000):
            continue
        x, y, z = _f32(ram, o + 0x2C), _f32(ram, o + 0x30), _f32(ram, o + 0x34)
        vx, vy, vz = (60.0 * _f32(ram, o + 0x50 + 4 * i) for i in range(3))
        if not all(np.isfinite(v) for v in (x, y, z, vx, vy, vz)):
            continue
        if cat in (CAT_STAGE, 2):
            # thrown / knocked stage objects, items and the cat-2 ground mover 0x0C16DBD4
            h = hist.get(k) if hist is not None else None
            if hist is not None:
                hist[k] = (vt, x, z, frame)
            if vt in STAGE_EXCLUDE or (cat == 2 and vt not in CAT2_MOVERS):
                continue
            sp, hsp = (vx * vx + vy * vy + vz * vz) ** 0.5, (vx * vx + vz * vz) ** 0.5
            if sp < (THROWN_MIN_SPEED if cat == CAT_STAGE else 300.0) or hsp < THROWN_MIN_HSPEED or sp > 8000:
                continue
            # observed motion must match the velocity field (kills stale +0x50 after a respawn)
            if h is None or h[0] != vt or not (0 < frame - h[3] < 30):
                continue
            dt = (frame - h[3]) / 60.0
            ox, oz = (x - h[1]) / dt, (z - h[2]) / dt
            if np.hypot(ox, oz) < THROWN_MIN_HSPEED or np.hypot(ox - vx, oz - vz) > 0.25 * hsp + 60.0:
                continue
            # held: within HELD_RADIUS of a fighter AND moving with it
            if player_vel is not None:
                dxz = np.hypot(player_pos[:, 0] - x, player_pos[:, 2] - z)
                rel = np.linalg.norm(player_vel - np.array([vx, vy, vz]), axis=1)
                if np.any((dxz < HELD_RADIUS) & (rel < 300.0)):
                    continue
            kind, own = "thrown", None
        else:
            kind, own = "hit", owner_seat(ram, o)
        out.append(dict(kind=kind, vt=vt, label=LABELS.get(vt, ""), slot=k, owner=own,
                        own=(own == bot_seat), pos=(x, y, z), vel=(vx, vy, vz),
                        radius=_f32(ram, o + 0x19C)))
    melee = []
    for s, p in enumerate(PLAYER_MAT):
        b = p - 0x490 - RAM_BASE
        d = _u32(ram, b + 0x414)
        dmg = int(ram[(d & 0x00FFFFFF) + 2]) if d else 0     # descriptor +2 (damage-like byte, unverified)
        melee.append(dict(seat=s, active=bool(d), move=int(ram[b + 0x134]), desc=d, dmg_byte=dmg))
    return dict(threats=out, melee=melee)


def obs_block(res, bot_pos, n=3, scale=(2000.0, 1000.0, 2000.0), vscale=3000.0):
    """Obs v4 proposal: n nearest enemy threats (own projectiles dropped), 9 dims each:
    dx, dy, dz (bot-relative, scaled), vx, vy, vz (scaled), radius/300, is_thrown, present."""
    bx, by, bz = bot_pos
    t = [r for r in res["threats"] if not r["own"]]
    t.sort(key=lambda r: (r["pos"][0] - bx) ** 2 + (r["pos"][2] - bz) ** 2)
    v = np.zeros((n, 9), np.float32)
    for i, r in enumerate(t[:n]):
        x, y, z = r["pos"]; vx, vy, vz = r["vel"]
        rad = r["radius"] if np.isfinite(r["radius"]) and 0 < r["radius"] < 2000 else 0.0
        v[i] = [(x - bx) / scale[0], (y - by) / scale[1], (z - bz) / scale[2],
                vx / vscale, vy / vscale, vz / vscale, rad / 300.0, float(r["kind"] == "thrown"), 1.0]
    return np.clip(v, -5, 5).ravel()
