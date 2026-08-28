"""Power Stone 2 guest-RAM addresses — single source of truth for the Linux port.

Every address here is a GUEST address (Dreamcast CPU view), copied from
RAM_MAP.md + the bridge calibration files (ps2_addr/players/gems/pool.txt,
which are identical across all savestate slots). They are emulator-independent:
under libretro, read at offset (addr - RAM_BASE) into the SYSTEM_RAM buffer.

If probe_ram.py reports a nonzero base delta, set RAM_DELTA accordingly —
every reader in ps2_ram.py applies it.
"""

RAM_BASE = 0x8C000000          # DC system RAM guest base (16 MiB)
RAM_SIZE = 16 * 1024 * 1024
RAM_DELTA = 0                  # probe_ram.py may discover an offset; set here

# --- 1. Health (floats, full = 1000.0), 4-byte stride --------------------
HEALTH = [0x8C475A04, 0x8C475A08, 0x8C475A0C, 0x8C475A10]   # P1..P4

# --- 2. Player render-matrix roots (0x3938 stride, savestate-independent) -
# lua v4 blocks: translation at +0x30/+0x34/+0x38 (x,y,z),
# facing row r0 at +0x00/+0x08 (NOT unit length — carries character scale).
PLAYER_MAT = [0x8C532928, 0x8C536260, 0x8C539B98, 0x8C53D4D0]  # P1..P4
MAT_POS = (0x30, 0x34, 0x38)
MAT_FACE = (0x00, 0x08)

# --- 3. Logic objects: (gem_count_byte_addr, F_anchor_addr) per player ----
# count byte = F+0x35 (HUD gauge, 0..3, holds 3 through a form);
# form flag = bit 0x00010000 of the F word (BIT test, never equality).
GEMS = [
    (0x8C535BE5, 0x8C535BB0),   # P1
    (0x8C53951D, 0x8C5394E8),   # P2  <- the bot on the Windows rig
    (0x8C53CE55, 0x8C53CE20),   # P3
    (0x8C54078D, 0x8C540758),   # P4
]
PF_METER = 0xA0     # form energy float, ~100 at transform -> 0.0 (drains)
PF_ITEMP = 0x54     # item DEFINITION POINTER — the identity key (never F+0x100)

# --- 4. Entity pool (stones / chests / items / projectiles share it) ------
# From ps2_pool.txt: base 0x8C3E7400, 160 slots (window widened from the
# RAM_MAP default 0x8C3EE000/64 — the first clip hid dropped stones).
POOL_BASE = 0x8C3E7400
POOL_SLOTS = 160
POOL_STRIDE = 0x90
POOL_ACTIVE = 0x34          # == 1 when the slot is live
POOL_CLASS = 0x3C           # instance pointer — the real identity marker
POOL_SPIN = 0x70            # spin-matrix word; CHANGES between reads for a
                            # real stone, FROZEN for an empty spawn pad
POOL_POS = (0x8C, 0x90, 0x94)   # x, y, z floats

STONE_CLASS_LO = 0x0C590000     # class window from ps2_pool.txt
STONE_CLASS_HI = 0x0C598000
STONE_DROPPED = {0x0C594100, 0x0C596E60}   # grounded / hovering dropped stone
                                            # (always real — no spin gate needed)

# --- 5b. Object ledger (STONE_OBJ_MODE — the Aug-10 doctrine flip) --------
# Kit #3 (powerstone.lua stoneObjScan + RAM_MAP §4): on these stages the
# pads hold CHESTS, not stones. The game's own object arena is the truth
# source: loose stones (the thing to chase), resting chests (the gem
# source), falling chests (counted). The legacy pool sweep misreports pad
# chests as stones — root cause of the Aug-24 parity fail.
STONE_OBJ_MODE = True        # False = legacy pool-whitelist sweep (pre-Aug-10)
OBJ_GRID_ANCHOR = 0x8C500030             # confirmed grid base (mod 0x430)
OBJ_GRID_STRIDE = 0x430
OBJ_GRID_LO = OBJ_GRID_ANCHOR - 16 * OBJ_GRID_STRIDE     # 0x8C4FBD30
OBJ_GRID_N = 110                         # ..0x8C5189C0, margin both ends
OBJ_HDR_OFF = 0x04           # low byte == 0x09 marks a live slot
OBJ_VT_OFF = 0x08            # vtable word, live range [0x0C000000,0x0C200000)
OBJ_POS = (0x2C, 0x30, 0x34)             # x, y, z floats
STONE_LOOSE_VT = 0x0C0CBCB0  # THE loose power stone (knock-outs, chest opens)
CHEST_REST_VT = 0x0C0CC7A8   # resting chest at a pad (y exactly 50)
CHEST_FALL_VT = 0x0C0C9810   # chest descending from the sky — count only
OBJ_KNOWN_UNREPORTED = {0x0C0CACAC, 0x0C0F18D4, 0x0C0F1688}  # absorb arc +
                                                             # static spawners

# --- 6. Projectiles -------------------------------------------------------
PROJ_CLASSES = {0x0C7F9A10: "rocket"}       # THE projectile (single record)
# Full exclusion list from powerstone.lua (kit #3) — the old 3-entry list
# let carried-stone visuals and junk through the velocity fallback.
PROJ_EXCLUDE = {
    0x0C7FA4B8,   # rocket visual mesh (same 1198 u/s — worst false positive)
    0x0C7FABC8,   # explosion (up to 20 records)
    0x0C7FCDF8,   # muzzle flash
    0x0C59C920, 0x0C59B270, 0x0C599BC0, 0x0C598510,   # carried-stone visuals
    0x0C594100,   # the Aug-6 "dropped stone" mislabel (carried visual)
    0x0C5957B0, 0x0C5936D0,                            # stationary junk
}
PROJ_EXCLUDE_BANDS = (
    (0x0C5D0000, 0x0C5E0000),   # chests — their own obs channel
    (0x0C610000, 0x0C620000),   # ground items
    (0x0C590000, 0x0C598000),   # classic stone band (lua excludes STONE_CLASSES)
)
PROJ_SPEED_MIN = 700.0                      # u/s fallback gate (players ~357)

# --- legacy line fields (kept for wire-format fidelity; env ignores them) -
G1_LEGACY = (0x8C5324AC, 1)   # (addr, byte width) — RETIRED counters, still
G2_LEGACY = (0x8C536214, 1)   # emitted as fields 10/11 of the v4+ line

# --- line cadence ---------------------------------------------------------
STONE_SCAN_EVERY = 3    # vblanks between pool sweeps (lua parity)
STONE_REPORT = 6        # stone triples on the v6 line
PROJ_REPORT = 2         # projectile slots on the line
