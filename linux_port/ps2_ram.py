"""Direct-RAM state reader for Power Stone 2 under libretro.

This is the Python port of powerstone.lua's read side. Instead of a lua
script writing ps2_state.txt once per vblank, we read the same guest
addresses straight out of the core's SYSTEM_RAM buffer (zero-copy numpy
view from RetroEmulator.get_ram()) and synthesize the SAME v7 state line
(80 fields, cmdseq last) that powerstone_env_v6._parse_state_once()
already knows how to parse. The env's parser, obs builder, reward path and
the trained model are all untouched.

Aug 28 (kit #3): STONE_OBJ_MODE ported from powerstone.lua's stoneObjScan.
The Aug-10 doctrine flip now applies here too: pads hold CHESTS, not
stones — stones on the line are the game's own object-ledger loose stones
(vt 0x0C0CBCB0), the chest fragment is live (chestN, fallN, 2 nearest
resting chests), and the legacy spin-gate pool sweep survives only as the
STONE_OBJ_MODE=False fallback. This closes the two obs gaps behind the
Aug-24 parity fail (chest dims dark + pad-chests misreported as stones).

Also Aug 28: the line is composed LAZILY — tick() updates caches, the
`line` property builds the string at most once per frame and only when
read (the env reads once per ~8.6 frames; composing every frame was +32%
on the whole loop, measured by bench_fps.py).
"""
import struct
import numpy as np

import ps2_addr as A


class PS2Ram:
    """Low-level typed reads on the SYSTEM_RAM numpy view (guest addrs)."""

    def __init__(self, ram: np.ndarray):
        self.ram = ram
        self.base = A.RAM_BASE + A.RAM_DELTA

    def _off(self, addr):
        o = addr - self.base
        if o < 0 or o + 4 > self.ram.size:
            raise ValueError(f"guest addr {addr:#x} outside RAM view")
        return o

    def u8(self, addr):
        return int(self.ram[self._off(addr)])

    def u32(self, addr):
        o = self._off(addr)
        return int(self.ram[o]) | int(self.ram[o+1]) << 8 \
            | int(self.ram[o+2]) << 16 | int(self.ram[o+3]) << 24

    def f32(self, addr):
        o = self._off(addr)
        return struct.unpack_from("<f", self.ram, o)[0]

    # vectorized helpers for strided sweeps ------------------------------
    def grid_words(self, base, stride, n, field_off):
        """u32 array at base + k*stride + field_off for k in [0, n)."""
        o0 = self._off(base) + field_off
        idx = o0 + np.arange(n) * stride
        r = self.ram
        return (r[idx].astype(np.uint32) | r[idx+1].astype(np.uint32) << 8 |
                r[idx+2].astype(np.uint32) << 16 | r[idx+3].astype(np.uint32) << 24)

    def grid_floats(self, base, stride, n, field_off):
        return np.frombuffer(
            self.grid_words(base, stride, n, field_off)
            .astype(np.uint32).tobytes(), dtype=np.float32)

    def pool_words(self, field_off):
        return self.grid_words(A.POOL_BASE, A.POOL_STRIDE, A.POOL_SLOTS,
                               field_off)

    def pool_floats(self, field_off):
        return self.grid_floats(A.POOL_BASE, A.POOL_STRIDE, A.POOL_SLOTS,
                                field_off)


def _fin(x, lo=-100000.0, hi=100000.0):
    return x == x and lo < x < hi


class StateLineSynth:
    """Produces the exact v7 (80-field) state line each frame.

    bot_player: 1-based DC player whose position sorts stones/projectiles/
    chests nearest-first (the Windows rig uses P2). For self-play, make one
    synth per agent.
    """

    ZERO_CHEST = "0,0,0.00,0.00,0.00,0.00,0.00,0.00"

    def __init__(self, ram: np.ndarray, bot_player: int = 2):
        self.r = PS2Ram(ram)
        self.bot = bot_player - 1
        self.frame = 0
        self._spin_prev = None          # spin words from the previous sweep
        self._proj_hist = {}            # slot -> (cls, x, y, z, frame)
        self._stone_cache = "0.00,0.00,0.00," * (A.STONE_REPORT - 1) + "0.00,0.00,0.00"
        self._chest_frag = self.ZERO_CHEST
        self._proj_cache = []
        self._scan_last = -10
        self._ack = 0
        self._line_frame = -1
        self._line_cache = ""

    # ------------------------------------------------------------------ IO
    def tick(self, ack: int):
        """Call once per emulated frame AFTER RetroEmulator.run().
        Updates caches only; the line composes lazily via the `line`
        property (at most once per frame, usually once per env step)."""
        self.frame += 1
        self._ack = ack
        if self.frame - self._scan_last >= A.STONE_SCAN_EVERY:
            self._scan_last = self.frame
            self._sweep_pool()

    @property
    def line(self):
        if self._line_frame != self.frame:
            if self.frame == 0:
                return ""
            self._line_cache = self._compose(self._ack)
            self._line_frame = self.frame
        return self._line_cache

    @line.setter
    def line(self, value):
        # selfplay_env._obs_from_view assigns line directly (save/assign/
        # restore around the parent obs builder). Pin the assigned value
        # for the current frame; the next tick() invalidates it naturally.
        self._line_cache = value
        self._line_frame = self.frame

    def on_loadstate(self):
        """Reset sweep history (pool slots are re-randomized by a loadstate)."""
        self._spin_prev = None
        self._proj_hist.clear()
        # frame counter keeps monotonically increasing on purpose: the env
        # only ever checks frame ADVANCE, and lua's counter also never reset.

    # ------------------------------------------------------------ helpers
    def _bot_xz(self):
        b = A.PLAYER_MAT[self.bot]
        try:
            x = self.r.f32(b + A.MAT_POS[0]); z = self.r.f32(b + A.MAT_POS[2])
            if _fin(x) and _fin(z):
                return x, z
        except ValueError:
            pass
        return None, None

    # ---- object ledger (STONE_OBJ_MODE, kit #3) -------------------------
    def _obj_scan(self):
        """Walk the game's object arena (lua stoneObjScan, ported 1:1).

        Returns (loose_stones, resting_chests, falling_count); positions
        are (x, z, y) triples, NaN/range-guarded like the lua (bad y -> 0).
        """
        r = self.r
        hdr = r.grid_words(A.OBJ_GRID_LO, A.OBJ_GRID_STRIDE, A.OBJ_GRID_N,
                           A.OBJ_HDR_OFF)
        vt = r.grid_words(A.OBJ_GRID_LO, A.OBJ_GRID_STRIDE, A.OBJ_GRID_N,
                          A.OBJ_VT_OFF)
        live = ((hdr & 0xFF) == 0x09) & (vt >= 0x0C000000) & (vt < 0x0C200000)
        interest = live & ((vt == A.STONE_LOOSE_VT) | (vt == A.CHEST_REST_VT)
                           | (vt == A.CHEST_FALL_VT))
        stones, chests, fall = [], [], 0
        if not interest.any():
            return stones, chests, fall
        xs = r.grid_floats(A.OBJ_GRID_LO, A.OBJ_GRID_STRIDE, A.OBJ_GRID_N,
                           A.OBJ_POS[0])
        ys = r.grid_floats(A.OBJ_GRID_LO, A.OBJ_GRID_STRIDE, A.OBJ_GRID_N,
                           A.OBJ_POS[1])
        zs = r.grid_floats(A.OBJ_GRID_LO, A.OBJ_GRID_STRIDE, A.OBJ_GRID_N,
                           A.OBJ_POS[2])
        for k in np.nonzero(interest)[0]:
            v = int(vt[k])
            if v == A.CHEST_FALL_VT:
                fall += 1
                continue
            x, y, z = float(xs[k]), float(ys[k]), float(zs[k])
            if _fin(x) and _fin(z):
                if not _fin(y):
                    y = 0.0
                (stones if v == A.STONE_LOOSE_VT else chests).append((x, z, y))
        return stones, chests, fall

    # ---- legacy pool stones (STONE_OBJ_MODE=False fallback) -------------
    def _legacy_stones(self, live, cls, spin, xs, ys, zs):
        in_band = live & (cls >= A.STONE_CLASS_LO) & (cls < A.STONE_CLASS_HI)
        dropped = np.isin(cls, list(A.STONE_DROPPED)) & live
        spinning = np.zeros_like(in_band)
        if self._spin_prev is not None:
            spinning = in_band & (spin != self._spin_prev)
        self._spin_prev = spin.copy()
        keep = dropped | (in_band & spinning)
        stones = []
        for k in np.nonzero(keep)[0]:
            x, y, z = float(xs[k]), float(ys[k]), float(zs[k])
            if _fin(x) and _fin(z) and (x != 0.0 or z != 0.0):
                stones.append((x, z, y))
        return stones

    # ------------------------------------------------------------- sweep
    def _sweep_pool(self):
        r = self.r
        act = r.pool_words(A.POOL_ACTIVE)
        cls = r.pool_words(A.POOL_CLASS)
        spin = r.pool_words(A.POOL_SPIN)
        xs = r.pool_floats(A.POOL_POS[0])
        ys = r.pool_floats(A.POOL_POS[1])
        zs = r.pool_floats(A.POOL_POS[2])
        live = act == 1
        bx, bz = self._bot_xz()

        # ---- stones + chests -------------------------------------------
        chests, fall = [], 0
        if A.STONE_OBJ_MODE:
            try:
                stones, chests, fall = self._obj_scan()
                # keep the spin history warm so a mode flip mid-run is sane
                self._spin_prev = spin.copy()
            except Exception:
                # lua parity: pcall(stoneObjScan) falls back to the pool
                stones = self._legacy_stones(live, cls, spin, xs, ys, zs)
        else:
            stones = self._legacy_stones(live, cls, spin, xs, ys, zs)

        if bx is not None:
            stones.sort(key=lambda s: (s[0]-bx)**2 + (s[1]-bz)**2)
            chests.sort(key=lambda c: (c[0]-bx)**2 + (c[1]-bz)**2)
        n_chests = len(chests)                 # count BEFORE the 2-slot cut
        stones = stones[:A.STONE_REPORT]
        parts = [f"{x:.2f},{z:.2f},{y:.2f}" for x, z, y in stones]
        parts += ["0.00,0.00,0.00"] * (A.STONE_REPORT - len(parts))
        self._stone_cache = ",".join(parts)
        cparts = [f"{c[0]:.2f},{c[1]:.2f},{c[2]:.2f}" for c in chests[:2]]
        cparts += ["0.00,0.00,0.00"] * (2 - len(cparts))
        self._chest_frag = f"{n_chests},{fall},{cparts[0]},{cparts[1]}"

        # ---- projectiles (class whitelist + velocity fallback) ----------
        counts = {}
        for k in np.nonzero(live)[0]:
            c = int(cls[k]); counts[c] = counts.get(c, 0) + 1
        out, seen = [], set()
        for k in np.nonzero(live)[0]:
            c = int(cls[k])
            x, y, z = float(xs[k]), float(ys[k]), float(zs[k])
            if not (_fin(x) and _fin(z)):
                self._proj_hist.pop(int(k), None)
                continue
            h = self._proj_hist.get(int(k))
            sp, vx, vz = None, 0.0, 0.0
            if h and h[0] == c and self.frame > h[4]:
                dt = (self.frame - h[4]) / 60.0
                if 0 < dt < 1.0:
                    dx, dz, dy = x - h[1], z - h[3], y - h[2]
                    sp = (dx*dx + dz*dz + dy*dy) ** 0.5 / dt
                    vx, vz = dx / dt, dz / dt
            self._proj_hist[int(k)] = (c, x, y, z, self.frame)
            known = c in A.PROJ_CLASSES
            banded = any(lo <= c < hi for lo, hi in A.PROJ_EXCLUDE_BANDS)
            if known or (sp and sp >= A.PROJ_SPEED_MIN and counts.get(c) == 1
                         and c not in A.PROJ_EXCLUDE and not banded):
                if c not in seen:
                    seen.add(c)
                    out.append((x, y, z, vx, vz))
        if bx is not None:
            out.sort(key=lambda p: (p[0]-bx)**2 + (p[2]-bz)**2)
        self._proj_cache = out[:A.PROJ_REPORT]

    # ----------------------------------------------------------- compose
    def _compose(self, ack: int) -> str:
        r = self.r
        h = []
        for a in A.HEALTH:
            try:
                v = r.f32(a)
            except ValueError:
                v = 0.0
            h.append(v if _fin(v, -1e6, 1e6) else 0.0)

        blocks = []
        for b in A.PLAYER_MAT:
            try:
                x = r.f32(b + A.MAT_POS[0]); y = r.f32(b + A.MAT_POS[1])
                z = r.f32(b + A.MAT_POS[2])
                fx = r.f32(b + A.MAT_FACE[0]); fz = r.f32(b + A.MAT_FACE[1])
                if all(_fin(v, -1e6, 1e6) for v in (x, y, z, fx, fz)):
                    blocks.append(f"{x:.2f},{y:.2f},{z:.2f},{fx:.4f},{fz:.4f}")
                else:
                    blocks.append("0,0,0,0,0")
            except ValueError:
                blocks.append("0,0,0,0,0")

        gparts, fparts, mparts, iparts = [], [], [], []
        for ca, fa in A.GEMS:
            try:
                g = r.u8(ca)
                fw = r.u32(fa)
                formed = 1 if (fw >> 16) & 1 else 0
                if 0 <= g <= 99:
                    gparts.append(str(g)); fparts.append(str(formed))
                else:
                    gparts.append("-1"); fparts.append("0")
                mt = r.f32(fa + A.PF_METER)
                if not (mt == mt and 0 <= mt <= 1000):
                    mt = 0.0
                mparts.append(f"{mt:.2f}")
                iparts.append(str(r.u32(fa + A.PF_ITEMP)))
            except ValueError:
                gparts.append("-1"); fparts.append("0")
                mparts.append("-1.00"); iparts.append("0")

        pparts = []
        for k in range(A.PROJ_REPORT):
            if k < len(self._proj_cache):
                x, y, z, vx, vz = self._proj_cache[k]
                pparts.append(f"{x:.2f},{y:.2f},{z:.2f},{vx:.2f},{vz:.2f}")
            else:
                pparts.append("0.00,0.00,0.00,0.00,0.00")

        g1 = r.u8(A.G1_LEGACY[0]); g2 = r.u8(A.G2_LEGACY[0])

        return (f"{self.frame},{h[0]:.2f},{h[1]:.2f},{h[2]:.2f},{h[3]:.2f},"
                f"{blocks[0]},{blocks[1]},{blocks[2]},{blocks[3]},"
                f"{g1},{g2},{self._stone_cache},"
                f"{','.join(gparts)},{','.join(fparts)},"
                f"{','.join(mparts)},{','.join(iparts)},"
                f"{pparts[0]},{pparts[1]},{self._chest_frag},{ack}\n")
