"""Raw emulator throughput, one process (Oct 1 2026, 9950X render study): load the mixed match state,
run FRAMES frames with neutral input, print fps. Launch N copies in parallel to measure scaling."""
import os, sys, time
from flycast_bridge import FlycastBridge
inst = int(sys.argv[1]); frames = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
b = FlycastBridge(os.path.expanduser("~/cores/flycast_libretro.so"), "../Power Stone 2 (USA).chd", "./states_mixed", inst)
b.loadstate(0); b.run_frames(60)
import numpy as np
r0 = np.asarray(b.emu.get_ram()).copy()
t = time.time(); b.run_frames(frames); dt = time.time() - t
r1 = np.asarray(b.emu.get_ram())
changed = int((r0 != r1).sum())   # bytes of game RAM that changed: ~0 means the core did not emulate
print(f"inst={inst} fps={frames/dt:.1f} ram_changed={changed}", flush=True)
