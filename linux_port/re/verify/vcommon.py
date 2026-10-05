"""Independent verifier helpers (instance 9). Own readers; does NOT import the RE agents' code."""
import gzip, os, struct, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, LP)
import numpy as np
from flycast_bridge import FlycastBridge

CORE = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
GAME = os.path.abspath(os.path.join(LP, "../Power Stone 2 (USA).chd"))
GRID = 0x8C4FBD30; STRIDE = 0x430
P0 = 0x8C532498; PSTR = 0x3938
BTN = dict(a=0x004, b=0x002, x=0x400, y=0x200, up=0x010, down=0x020, left=0x040, right=0x080)

class V:
    def __init__(self):
        os.chdir(LP)
        self.br = FlycastBridge(CORE, GAME, "./states", instance_id=9)
        self.ram = self.br.ram
        self.br.run_frames(4)
        self._blobs = {}
    # ---- state
    def load(self, name):
        if name not in self._blobs:
            p = name if os.path.exists(name) else f"states/{name}.state"
            self._blobs[name] = gzip.open(p).read() if p.endswith(".state") and open(p,'rb').read(2)==b'\x1f\x8b' else open(p,'rb').read()
        self.br.emu.set_state(self._blobs[name]); self.br.clear_inputs()
    def snap(self): return bytes(self.br.emu.get_state())
    def restore(self, blob): self.br.emu.set_state(blob); self.br.clear_inputs()
    def run(self, n=1): self.br.run_frames(n)
    def hold(self, mask, player):  # set mask without running
        self.br.press(mask, 0, player=player)
    # ---- raw RAM
    def o(self, a): return a & 0xFFFFFF
    def u8(self, a): return int(self.ram[self.o(a)])
    def u16(self, a): return struct.unpack_from("<H", self.ram, self.o(a))[0]
    def u32(self, a): return struct.unpack_from("<I", self.ram, self.o(a))[0]
    def f32(self, a): return struct.unpack_from("<f", self.ram, self.o(a))[0]
    def w8(self, a, v): self.ram[self.o(a)] = v & 0xFF
    def w16(self, a, v): struct.pack_into("<H", self.ram, self.o(a), v & 0xFFFF)
    def w32(self, a, v): struct.pack_into("<I", self.ram, self.o(a), v & 0xFFFFFFFF)
    def wf(self, a, v): struct.pack_into("<f", self.ram, self.o(a), float(v))
    def ramhash(self): return hashlib.md5(bytes(self.ram)).hexdigest()
    # ---- player
    def P(self, k): return P0 + k * PSTR
    def hp(self, k): return self.f32(self.P(k) + 0x160)
    def pos(self, k): return tuple(self.f32(self.P(k) + 0x28 + 4*i) for i in range(3))
    def pstate(self, k): return self.u8(self.P(k) + 0x3715)
    def com(self, k): return self.u8(self.P(k) + 0x3720)
    def char(self, k): return self.u8(self.P(k) + 2)
    def heldptr(self, k): return self.u32(self.P(k) + 0x3718 + 0x54)
    # ---- ledger
    def rec(self, i): return GRID + i * STRIDE
    def records(self, lo=0, hi=208):
        out = []
        for i in range(lo, hi):
            r = self.rec(i); h = self.u32(r + 4)
            if h & 0xFF == 0: continue
            out.append(dict(i=i, a=r, cat=h & 0xFF, hold=(h >> 8) & 0xFF, vt=self.u32(r + 8),
                            tid=self.u8(r + 0x420), st=self.u8(r + 0x421), uses=self.u16(r + 0x424),
                            content=self.u8(r + 0x42C),
                            x=self.f32(r + 0x2C), y=self.f32(r + 0x30), z=self.f32(r + 0x34)))
        return out
    def shot(self, path):
        import pygame
        h, w = self.br.emu.get_shape()
        arr = np.zeros((h, w, 3), np.uint8)
        self.br.emu.get_frame(arr, w, h)
        arr = arr[::-1].copy()
        pygame.image.save(pygame.surfarray.make_surface(arr.swapaxes(0, 1)), path)
        return path

    # ---- fast vectorised ledger table (copies 208 records)
    def table(self):
        base = GRID & 0xFFFFFF
        reg = np.array(self.ram[base: base + 208 * STRIDE]).reshape(208, STRIDE)
        t = {}
        t['cat'] = reg[:, 4].astype(int)
        t['vt'] = reg[:, 8:12].copy().view('<u4')[:, 0].astype(np.int64)
        t['ser'] = reg[:, 0x28:0x2C].copy().view('<u4')[:, 0].astype(np.int64)
        xyz = reg[:, 0x2C:0x38].copy().view('<f4')
        t['x'], t['y'], t['z'] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
        t['tid'] = reg[:, 0x420].astype(int); t['st'] = reg[:, 0x421].astype(int)
        t['uses'] = reg[:, 0x424:0x426].copy().view('<u2')[:, 0].astype(int)
        t['content'] = reg[:, 0x42C].astype(int)
        return t
    def refill(self):
        for k in range(4):
            if self.f32(self.P(k) + 0x160) > 0: self.wf(self.P(k) + 0x160, 1000.0)
