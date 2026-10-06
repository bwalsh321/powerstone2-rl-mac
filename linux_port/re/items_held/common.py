"""Shared helpers for the held-item RE probes. instance_id=1 ONLY."""
import gzip, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, LP)
os.chdir(LP)
from flycast_bridge import FlycastBridge  # noqa
import ps2_addr as A  # noqa

CORE = os.path.expanduser(
    "~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
GAME = os.path.join(LP, "../Power Stone 2 (USA).chd")
F = [g[1] for g in A.GEMS]
BTN = {"a": 0x004, "b": 0x002, "x": 0x400, "y": 0x200, "start": 0x008,
       "up": 0x010, "down": 0x020, "left": 0x040, "right": 0x080}


def boot():
    br = FlycastBridge(CORE, GAME, "./states", instance_id=1)
    br.run_frames(8)
    return br


def load(br, path):
    with gzip.open(path, "rb") as f:
        br.emu.set_state(f.read())
    br.clear_inputs()
    br.run_frames(4)


def save(br, path):
    with gzip.open(path, "wb") as f:
        f.write(br.emu.get_state())


def off(a):
    return (a & 0x00FFFFFF)


def u32(ram, a):
    o = off(a)
    return int(ram[o]) | int(ram[o+1]) << 8 | int(ram[o+2]) << 16 | int(ram[o+3]) << 24


def u16(ram, a):
    o = off(a)
    return int(ram[o]) | int(ram[o+1]) << 8


def f32(ram, a):
    return struct.unpack("<f", bytes(ram[off(a):off(a)+4]))[0]


def words(ram, a, n):
    o = off(a)
    return np.frombuffer(bytes(ram[o:o+4*n]), dtype="<u4")


def shot(br, path):
    import pygame
    h, w = br.emu.get_shape()
    arr = np.zeros((h, w, 3), np.uint8)
    br.emu.get_frame(arr, w, h)
    arr = arr[::-1]  # frames come out vertically flipped
    surf = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
    pygame.image.save(surf, path)


def refill(ram):
    """Keep everyone alive (HEALTH_OBJ primary + display mirrors), per ps2_addr notes."""
    pk = np.frombuffer(struct.pack("<f", 1000.0), dtype=np.uint8)
    for a in list(A.HEALTH_OBJ) + list(A.HEALTH) + [h + 0x30 for h in A.HEALTH] + [h + 0x50 for h in A.HEALTH]:
        o = off(a); ram[o:o+4] = pk
