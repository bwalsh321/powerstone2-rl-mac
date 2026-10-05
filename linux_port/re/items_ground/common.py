"""Shared helpers for the items_ground RE scripts (instance_id=2 ONLY).

Run from linux_port/:
  source ~/ps2rl/bin/activate
  export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.:re/items_ground
"""
import gzip
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, LP)

from flycast_bridge import FlycastBridge  # noqa: E402
import ps2_addr as A  # noqa: E402

CORE = os.path.expanduser(
    "~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
GAME = os.path.join(LP, "../Power Stone 2 (USA).chd")
BASE = 0x8C000000

BTN = {"a": 0x004, "b": 0x002, "x": 0x400, "y": 0x200, "start": 0x008,
       "up": 0x010, "down": 0x020, "left": 0x040, "right": 0x080}


def boot():
    br = FlycastBridge(CORE, GAME, os.path.join(LP, "states"), instance_id=2)
    br.run_frames(8)
    return br


def load(br, slot):
    with gzip.open(os.path.join(LP, "states", f"slot{slot}.state")) as f:
        br.emu.set_state(f.read())
    br.clear_inputs()
    br.run_frames(4)


def off(addr):
    return (addr & 0x00FFFFFF)


def u32(ram, addr):
    o = off(addr)
    return int(ram[o]) | int(ram[o+1]) << 8 | int(ram[o+2]) << 16 | int(ram[o+3]) << 24


def u16(ram, addr):
    o = off(addr)
    return int(ram[o]) | int(ram[o+1]) << 8


def u8(ram, addr):
    return int(ram[off(addr)])


def f32(ram, addr):
    return struct.unpack_from("<f", ram, off(addr))[0]


def words(ram, base, stride, n, fo):
    o0 = off(base) + fo
    idx = o0 + np.arange(n) * stride
    r = ram
    return (r[idx].astype(np.uint32) | r[idx+1].astype(np.uint32) << 8 |
            r[idx+2].astype(np.uint32) << 16 | r[idx+3].astype(np.uint32) << 24)


def floats(ram, base, stride, n, fo):
    return words(ram, base, stride, n, fo).astype(np.uint32).view(np.float32)


# --------------------------------------------------------------- ledger
LED_LO = A.OBJ_GRID_LO
LED_N = A.OBJ_GRID_N


def ledger(ram, lo=LED_LO, n=LED_N):
    """list of (slot, addr, hdr, vt, x, y, z) for live ledger slots."""
    hdr = words(ram, lo, 0x430, n, 4)
    vt = words(ram, lo, 0x430, n, 8)
    xs = floats(ram, lo, 0x430, n, 0x2C)
    ys = floats(ram, lo, 0x430, n, 0x30)
    zs = floats(ram, lo, 0x430, n, 0x34)
    live = ((hdr & 0xFF) == 0x09) & (vt >= 0x0C000000) & (vt < 0x0C200000)
    out = []
    for k in np.nonzero(live)[0]:
        out.append((int(k), lo + int(k) * 0x430, int(hdr[k]), int(vt[k]),
                    float(xs[k]), float(ys[k]), float(zs[k])))
    return out


def pool(ram):
    act = words(ram, A.POOL_BASE, 0x90, A.POOL_SLOTS, 0x34)
    cls = words(ram, A.POOL_BASE, 0x90, A.POOL_SLOTS, 0x3C)
    xs = floats(ram, A.POOL_BASE, 0x90, A.POOL_SLOTS, 0x8C - 0x0)
    out = []
    for k in np.nonzero(act == 1)[0]:
        a = A.POOL_BASE + int(k) * 0x90
        out.append((int(k), a, int(cls[k])))
    return out


def player_xyz(ram, p):
    b = A.PLAYER_MAT[p]
    return (f32(ram, b + 0x30), f32(ram, b + 0x34), f32(ram, b + 0x38))


def held_item(ram, p):
    return u32(ram, A.GEMS[p][1] + 0x54)


def shot(br, path):
    import pygame
    h, w = br.emu.get_shape()
    arr = np.zeros((h, w, 3), np.uint8)
    br.emu.get_frame(arr, w, h)
    arr = arr[::-1].copy()          # frames come out vertically flipped
    surf = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
    pygame.image.save(surf, path)
    return path


class RandomPad:
    """Random-ish inputs for all 4 ports (held for a few frames)."""

    def __init__(self, seed=0, players=(0, 1), grab_bias=0.2):
        self.rng = np.random.default_rng(seed)
        self.players = players
        self.grab_bias = grab_bias

    def mask(self):
        r = self.rng
        m = 0
        d = r.integers(0, 9)
        m |= [0, 0x10, 0x20, 0x40, 0x80, 0x50, 0x90, 0x60, 0xA0][d]
        u = r.random()
        if u < 0.25:
            m |= 0x004  # A (punch)
        elif u < 0.25 + self.grab_bias:
            m |= 0x400  # X  (pick up / use)
        elif u < 0.6:
            m |= 0x002  # B
        elif u < 0.7:
            m |= 0x200  # Y
        return m

    def step(self, br, frames):
        for p in self.players:
            m = self.mask()
            mm = np.zeros(16, np.uint8)
            from flycast_bridge import DC_TO_RETRO
            for bit, rid in DC_TO_RETRO.items():
                if m & bit:
                    mm[rid] = 1
            br.emu.set_button_mask(mm, p)
        br.run_frames(frames)
