"""stage_geom.py -- obs-v4 spatial block for the Power Stone 2 bot (stage geometry / spatial awareness).

Self-contained, numpy only, ~130 us per call on the M-series Mac (t_stage_geom.py); the 0.7 s per-stage precompute
runs once at import. Drop-in for powerstone_env_v6.py (see STAGE.md section 7).

What it encodes (all in the ACTION FRAME: ray k points where dpad direction k actually moves the fighter):
  [0:8]   wall/obstacle distance along the 8 dpad directions, normalised d/RAY_MAX, 1.0 = nothing within RAY_MAX
            static part  : stage bounds (desert: the +-1140 clamp box) from a precomputed per-stage grid
            dynamic part : the stage props read LIVE from the object ledger (poles, cactus clusters), ray-vs-circle
  [8:10]  vector to the nearest pole (action frame, /POS_SCALE), [10] its distance/POS_SCALE
  [11:13] vector to the nearest movable prop (cactus cluster), [13] distance/POS_SCALE
  [14:16] vector to the nearest boundary point (action frame), [16] distance/POS_SCALE   ("nearest edge/wall")
  [17]    floor height under me minus my y / HEIGHT_SCALE (0 on flat stages; >0 = I am airborne above floor)
  [18:26] floor height 150 u ahead in each dpad direction minus floor under me / HEIGHT_SCALE  ("ledge / step ahead")
  [26]    stage-has-map flag (1 if a geometry map exists for the live stage id, else the block is all zeros)
SPATIAL_DIM = 27

Coordinate conventions: world x, z = logical position (player struct P = 0x8C532498 + i*0x3938; x,y,z at P+0x28/+0x2C/+0x30), y up (feet; 0 = desert floor).
"""
import struct
import numpy as np

SPATIAL_DIM = 27
RAY_MAX = 1000.0
POS_SCALE = 1000.0
HEIGHT_SCALE = 500.0
AHEAD = 150.0

# ---- RAM cells (STAGE.md) ------------------------------------------------------------------
STAGE_ID_ADDR = 0x8C46E198        # u32: 0 bluesky 1 darkcastle 2 tomb 3 iceberg 4 spacestation 5 desert/pharaoh 6 chaos
STAGE_VARIANT_ADDR = 0x8C54235E   # u8: 0 normal, 1 pharaoh-walker (on stage 5), 2 chaos
LEDGER_LO, LEDGER_STRIDE, LEDGER_N = 0x8C4FBD30, 0x430, 170
POLE_VT = 0x0C0F18D4              # desert tall cactus: fixed, r_eff 75 (player-centre pushout distance)
CLUSTER_VT = 0x0C0F1688           # desert cactus cluster: pushable, r_eff ~120
PROP_RADIUS = {POLE_VT: 75.0, CLUSTER_VT: 120.0}
PROP_Y_GATE = {POLE_VT: 400.0, CLUSTER_VT: 300.0}   # |prop y - my y| beyond this -> ignore (GUESS-level gate)

# dpad direction -> world (x, z) unit vector, per stage id (measured, s16_dpad_all.py). Order = action_space DIRS[1:]:
# up, down, left, right, up-left, up-right, down-left, down-right
_S = 0.7071067811865476
DPAD_WORLD_DESERT = np.array([[-_S, -_S], [_S, _S], [-_S, _S], [_S, -_S],
                              [-1, 0], [0, -1], [0, 1], [1, 0]], np.float32)
DPAD_WORLD = {5: DPAD_WORLD_DESERT}
CAM_BACK_ADDR = 0x8C541194        # f32 x3: unit vector target->eye (s18/s19). dpad 'up' == -(back) on xz, all 8 stages
CAM_EYE_ADDR = 0x8C5411A4         # f32 x3: camera eye position (LIKELY)


def dpad_dirs_from_camera(ram):
    """[8,2] world unit vectors of the 8 dpad directions, derived from the live camera yaw (exact on all stages, s19)."""
    bx = _rd_f32(ram, CAM_BACK_ADDR); bz = _rd_f32(ram, CAM_BACK_ADDR + 8)
    n = (bx * bx + bz * bz) ** 0.5
    if not np.isfinite(n) or n < 1e-3:
        return DPAD_WORLD_DESERT
    ux, uz = -bx / n, -bz / n                # up
    rx, rz = -uz, ux                         # right = up rotated -90 deg (desert: up (-1,-1)/r2 -> right (1,-1)/r2)
    s = 0.7071067811865476
    up, right = np.array([ux, uz]), np.array([rx, rz])
    return np.array([up, -up, -right, right, (up - right) * s, (up + right) * s, (-up - right) * s, (-up + right) * s],
                    np.float32)


def _rd_u32(ram, a):
    return struct.unpack_from("<I", ram, a & 0xFFFFFF)[0]


def _rd_f32(ram, a):
    return struct.unpack_from("<f", ram, a & 0xFFFFFF)[0]


class StageMap:
    """Per-stage static map: walkable grid + floor-height grid on a regular xz lattice, plus precomputed
    static ray distances for the 8 dpad directions (so the per-step cost is one lookup)."""

    def __init__(self, x0, z0, res, walk, floor, dirs):
        self.x0, self.z0, self.res = float(x0), float(z0), float(res)
        self.walk = walk.astype(bool)          # [Z, X]
        self.floor = floor.astype(np.float32)  # [Z, X] standable floor y (nan = none)
        self.dirs = dirs.astype(np.float32)    # [8, 2]
        self.ray = self._precompute_rays()     # [8, Z, X] distance to first non-walkable cell (capped RAY_MAX)
        self.bdist, self.bvec = self._precompute_boundary()

    @classmethod
    def box(cls, half=1140.0, res=10.0, dirs=DPAD_WORLD_DESERT, margin=40.0):
        """Analytic map for a flat square arena |x|,|z| <= half (the desert clamp box)."""
        xs = np.arange(-half - margin, half + margin + 1e-6, res)
        X, Z = np.meshgrid(xs, xs)
        walk = (np.abs(X) <= half) & (np.abs(Z) <= half)
        floor = np.where(walk, 0.0, np.nan)
        return cls(xs[0], xs[0], res, walk, floor, dirs)

    @classmethod
    def load(cls, path, dirs):
        d = np.load(path)
        return cls(d["x0"], d["z0"], d["res"], d["walk"], d["floor"], dirs)

    def _idx(self, x, z):
        ix = int(round((x - self.x0) / self.res)); iz = int(round((z - self.z0) / self.res))
        return min(max(iz, 0), self.walk.shape[0] - 1), min(max(ix, 0), self.walk.shape[1] - 1)

    def _precompute_rays(self):
        """[8,Z,X]: world-space march from every cell centre in steps of res/2; first blocked (or off-map) sample wins."""
        Z, X = self.walk.shape
        zz, xx = np.mgrid[0:Z, 0:X]
        cx = self.x0 + xx * self.res; cz = self.z0 + zz * self.res
        out = np.full((8, Z, X), RAY_MAX, np.float32)
        step = self.res / 2.0
        for k, (dx, dz) in enumerate(self.dirs):
            done = ~self.walk.copy()
            hit = np.where(done, 0.0, RAY_MAX).astype(np.float32)
            for t in np.arange(step, RAY_MAX + step, step):
                ix = np.rint((cx + dx * t - self.x0) / self.res).astype(np.int64)
                iz = np.rint((cz + dz * t - self.z0) / self.res).astype(np.int64)
                off = (ix < 0) | (ix >= X) | (iz < 0) | (iz >= Z)
                blk = off.copy()
                blk[~off] = ~self.walk[iz[~off], ix[~off]]
                new = blk & ~done
                hit[new] = t - step / 2.0
                done |= blk
                if done.all():
                    break
            out[k] = np.minimum(hit, RAY_MAX)
        return out

    def _precompute_boundary(self):
        """distance + vector to nearest non-walkable cell (brute force on the boundary set, done once)."""
        Z, X = self.walk.shape
        blk = ~self.walk
        nb = np.zeros_like(blk)                       # blocked cells that touch a walkable cell (the boundary)
        nb[1:] |= self.walk[:-1]; nb[:-1] |= self.walk[1:]; nb[:, 1:] |= self.walk[:, :-1]; nb[:, :-1] |= self.walk[:, 1:]
        b = np.argwhere(blk & nb)
        zz, xx = np.mgrid[0:Z, 0:X]
        bd = np.full((Z, X), RAY_MAX, np.float32); bv = np.zeros((Z, X, 2), np.float32)
        if len(b):
            # chunked nearest-neighbour (grid is small: ~240x240 at res 10 for the desert)
            pts = np.stack([zz.ravel(), xx.ravel()], 1).astype(np.float32); b = b.astype(np.float32)
            best = np.full(len(pts), np.inf); arg = np.zeros(len(pts), int)
            for j in range(0, len(b), 128):
                bb = b[j:j + 128]
                d2 = ((pts[:, None, :] - bb[None, :, :]) ** 2).sum(-1)
                m = d2.argmin(1); v = d2[np.arange(len(pts)), m]
                upd = v < best; best[upd] = v[upd]; arg[upd] = m[upd] + j
            near = b[arg]
            best[blk.ravel()] = 0.0; near[blk.ravel()] = pts[blk.ravel()]
            bd = (np.sqrt(best) * self.res).reshape(Z, X).astype(np.float32)
            bv = ((near - pts)[:, ::-1] * self.res).reshape(Z, X, 2).astype(np.float32)   # (dx, dz)
        scale = np.minimum(1.0, RAY_MAX / np.maximum(bd, 1e-6))[..., None]      # cap vector length at RAY_MAX too
        return np.minimum(bd, RAY_MAX), (bv * scale).astype(np.float32)

    def floor_at(self, x, z):
        iz, ix = self._idx(x, z)
        return self.floor[iz, ix]


def ray_circle(px, pz, dirs, cx, cz, r):
    """distance along each unit dir from (px,pz) to circle (cx,cz,r); RAY_MAX if missed/behind. dirs [8,2]."""
    ox, oz = cx - px, cz - pz
    b = dirs[:, 0] * ox + dirs[:, 1] * oz
    c = ox * ox + oz * oz - r * r
    disc = b * b - c
    t = b - np.sqrt(np.maximum(disc, 0.0))
    out = np.where((disc >= 0) & (b > 0), np.maximum(t, 0.0), RAY_MAX)
    return np.where(c <= 0, 0.0, out)        # already inside the pushout radius


def read_props(ram):
    """[(vtable, x, z, y)] for every live ledger object whose vtable is a known stage prop (resting y: pole 0, cluster 100)."""
    out = []
    for k in range(LEDGER_N):
        a = LEDGER_LO + k * LEDGER_STRIDE
        if (_rd_u32(ram, a + 4) & 0xFF) != 0x09:
            continue
        vt = _rd_u32(ram, a + 8)
        if vt in PROP_RADIUS:
            out.append((vt, _rd_f32(ram, a + 0x2C), _rd_f32(ram, a + 0x34), _rd_f32(ram, a + 0x30)))
    return out


class SpatialEncoder:
    """Usage in the env:  enc = SpatialEncoder();  vec = enc(ram, my_x, my_y, my_z)   (27 float32)."""

    def __init__(self, maps=None):
        # stage id -> StageMap. Desert (5) ships analytic; others load from data/map_<stage>.npz when present.
        self.maps = maps if maps is not None else {5: StageMap.box()}
        self._props_cache = (None, None)

    def to_action_frame(self, dirs, vx, vz):
        """world (vx, vz) -> (along dpad 'right', along dpad 'up') so the policy reads it in its own action frame."""
        right, up = dirs[3], dirs[0]
        return vx * right[0] + vz * right[1], vx * up[0] + vz * up[1]

    def __call__(self, ram, x, y, z, props=None):
        v = np.zeros(SPATIAL_DIM, np.float32)
        sid = _rd_u32(ram, STAGE_ID_ADDR)
        variant = ram[STAGE_VARIANT_ADDR & 0xFFFFFF]
        m = self.maps.get(sid) if variant == 0 else None
        if m is None:
            return v
        dirs = m.dirs
        iz, ix = m._idx(x, z)
        rays = m.ray[:, iz, ix].copy()
        props = read_props(ram) if props is None else props
        best = {POLE_VT: (np.inf, 0.0, 0.0), CLUSTER_VT: (np.inf, 0.0, 0.0)}
        for pr in props:
            vt, cx, cz = pr[0], pr[1], pr[2]
            if len(pr) > 3 and abs(pr[3] - y) > PROP_Y_GATE.get(vt, 1e9):
                continue                     # prop carried / thrown / far below: not a wall at my height
            r = PROP_RADIUS[vt]
            rays = np.minimum(rays, ray_circle(x, z, dirs, cx, cz, r))
            d = np.hypot(cx - x, cz - z)
            if d < best[vt][0]:
                best[vt] = (d, cx - x, cz - z)
        v[0:8] = np.clip(rays / RAY_MAX, 0.0, 1.0)
        for base, vt in ((8, POLE_VT), (11, CLUSTER_VT)):
            d, dx, dz = best[vt]
            if np.isfinite(d):
                a, b = self.to_action_frame(dirs, dx, dz)
                v[base:base + 3] = (a / POS_SCALE, b / POS_SCALE, d / POS_SCALE)
        bd = m.bdist[iz, ix]; bx, bz = m.bvec[iz, ix]
        a, b = self.to_action_frame(dirs, bx, bz)
        v[14:17] = (a / POS_SCALE, b / POS_SCALE, bd / POS_SCALE)
        f0 = m.floor[iz, ix]
        f0 = 0.0 if not np.isfinite(f0) else f0
        v[17] = (y - f0) / HEIGHT_SCALE
        for k in range(8):
            fa = m.floor_at(x + dirs[k, 0] * AHEAD, z + dirs[k, 1] * AHEAD)
            v[18 + k] = ((fa if np.isfinite(fa) else -HEIGHT_SCALE) - f0) / HEIGHT_SCALE
        v[26] = 1.0
        return v
