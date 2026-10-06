"""Shared harness for player_state RE experiments (instance_id=3 only)."""
import gzip, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, LP); sys.path.insert(0, os.path.join(LP, "..", "sdlarch-rl"))
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from flycast_bridge import FlycastBridge
import ps2_addr as A

CORE = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
GAME = os.path.join(LP, "..", "Power Stone 2 (USA).chd")
BTN = {"a": 0x004, "b": 0x002, "x": 0x400, "y": 0x200, "start": 0x008,
       "up": 0x010, "down": 0x020, "left": 0x040, "right": 0x080, "none": 0}

def boot():
    br = FlycastBridge(CORE, GAME, os.path.join(LP, "states"), instance_id=3)
    br.run_frames(8)
    return br

def load(br, path):
    if not os.path.isabs(path):
        path = os.path.join(LP, path)
    with gzip.open(path, "rb") as f:
        br.emu.set_state(f.read())
    br.clear_inputs()
    br.run_frames(2)

def snap(br):
    return br.ram.copy()

def off(a):
    return (a & 0xFFFFFF)

def u32(r, a):
    return struct.unpack_from("<I", r, off(a))[0]
def u16(r, a):
    return struct.unpack_from("<H", r, off(a))[0]
def u8(r, a):
    return int(r[off(a)])
def f32(r, a):
    return struct.unpack_from("<f", r, off(a))[0]

def shot(br, path):
    import pygame
    h, w = br.emu.get_shape()
    arr = np.zeros((h, w, 3), np.uint8)
    br.emu.get_frame(arr, w, h)
    arr = arr[::-1]   # frames come vertically flipped
    surf = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
    pygame.image.save(surf, path)

F = [g[1] for g in A.GEMS]
MAT = A.PLAYER_MAT

def record(br, steps, regions, player=0, shots_at=None, shot_prefix=None):
    """steps: list of (btn-name-or-mask, frames). Returns dict region->array[T, n] u8
    and list of labels per frame. Snapshot taken after every single frame."""
    out = {k: [] for k in regions}
    labels = []
    t = 0
    for btn, n in steps:
        if isinstance(btn, str):
            mask = 0
            for b in btn.split("+"): mask |= BTN[b]
        else:
            mask = btn
        m = np.zeros(16, np.uint8)
        from flycast_bridge import DC_TO_RETRO
        for bit, rid in DC_TO_RETRO.items():
            if mask & bit: m[rid] = 1
        br.emu.set_button_mask(m, player)
        for _ in range(n):
            br.emu.run()
            for k, (lo, hi) in regions.items():
                out[k].append(br.ram[off(lo):off(hi)].copy())
            labels.append(btn if isinstance(btn, str) else hex(btn))
            if shots_at and t in shots_at:
                shot(br, f"{shot_prefix}_{t:04d}.png")
            t += 1
    return {k: np.stack(v) for k, v in out.items()}, labels

def as_f32(a):
    return a.view("<f4")
def as_u32(a):
    return a.view("<u4")

P0 = 0x8C532498          # P1 player struct base (hard-coded in game code literal pools)
PSTRIDE = 0x3938
P = [P0 + i * PSTRIDE for i in range(4)]
def preg(i):
    return (P[i], P[i] + PSTRIDE)

def wf32(br, a, v):
    struct.pack_into("<f", br.ram, off(a), v)

def place(br, i, x, y, z):
    """Teleport player i (logical pos P+0x28 and logic-matrix translation P+0x94)."""
    for k, v in enumerate((x, y, z)):
        wf32(br, P[i] + 0x28 + 4*k, v)
        wf32(br, P[i] + 0x94 + 4*k, v)

def ppos(r, i):
    return [round(f32(r, P[i] + 0x28 + 4*k), 1) for k in range(3)]
