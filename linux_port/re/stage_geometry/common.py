"""Shared harness for stage_geometry RE (instance_id=5 ONLY)."""
import gzip, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, LP); sys.path.insert(0, os.path.join(LP, "..", "sdlarch-rl"))
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from flycast_bridge import FlycastBridge, DC_TO_RETRO
import ps2_addr as A

CORE = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
GAME = os.path.join(LP, "..", "Power Stone 2 (USA).chd")
BTN = {"a": 0x004, "b": 0x002, "x": 0x400, "y": 0x200, "start": 0x008,
       "up": 0x010, "down": 0x020, "left": 0x040, "right": 0x080, "none": 0}
INSTANCE = 5

def boot():
    br = FlycastBridge(CORE, GAME, os.path.join(LP, "states"), instance_id=INSTANCE)
    br.run_frames(8)
    return br

def load(br, path):
    if not os.path.isabs(path):
        path = os.path.join(LP, path)
    with gzip.open(path, "rb") as f:
        ok = br.emu.set_state(f.read())
    br.clear_inputs()
    br.run_frames(2)
    return ok

def off(a): return a & 0xFFFFFF
def u32(r, a): return struct.unpack_from("<I", r, off(a))[0]
def u16(r, a): return struct.unpack_from("<H", r, off(a))[0]
def u8(r, a): return int(r[off(a)])
def f32(r, a): return struct.unpack_from("<f", r, off(a))[0]
def wf32(br, a, v): struct.pack_into("<f", br.ram, off(a), v)

def mask_of(btn):
    if isinstance(btn, int): return btn
    m = 0
    for b in btn.split("+"):
        m |= BTN[b]
    return m

def setpad(br, btn, player=1):
    m = np.zeros(16, np.uint8)
    mask = mask_of(btn)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, player)

def shot(br, path):
    import pygame
    h, w = br.emu.get_shape()
    arr = np.zeros((h, w, 3), np.uint8)
    br.emu.get_frame(arr, w, h)
    arr = arr[::-1]
    surf = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
    pygame.image.save(surf, path)

MAT = A.PLAYER_MAT
P0 = 0x8C532498           # player struct base (re/player_state/harness.py)
PSTRIDE = 0x3938
P = [P0 + i * PSTRIDE for i in range(4)]

def matpos(r, i):
    return [f32(r, MAT[i] + 0x30), f32(r, MAT[i] + 0x34), f32(r, MAT[i] + 0x38)]
def logpos(r, i):
    return [f32(r, P[i] + 0x28 + 4 * k) for k in range(3)]
def pstate(r, i):
    return u8(r, MAT[i] + A.PSTATE_OFF)

def place(br, i, x, y, z):
    for k, v in enumerate((x, y, z)):
        wf32(br, P[i] + 0x28 + 4 * k, v)
        wf32(br, P[i] + 0x94 + 4 * k, v)

STATES = {
    "slot1": "states/slot1.state",
    "slot2": "states/slot2.state",
    "slot3": "states/slot3.state",
}

SG = os.path.join(HERE, "states")
STAGE_STATES = {"desert": os.path.join(LP, "states/slot1.state"),
                **{n: os.path.join(SG, f"{n}.state") for n in
                   ("bluesky", "darkcastle", "tomb", "iceberg", "spacestation", "desert_menu", "pharaoh", "chaos")}}

def ledger(r, n=A.OBJ_GRID_N + 60):
    out = []
    for k in range(n):
        a = A.OBJ_GRID_LO + k * A.OBJ_GRID_STRIDE
        if (u32(r, a + 4) & 0xFF) != 0x09: continue
        out.append((k, a, u32(r, a + 8), [f32(r, a + o) for o in A.OBJ_POS]))
    return out

def health(r, i):
    return f32(r, A.HEALTH_OBJ[i])
