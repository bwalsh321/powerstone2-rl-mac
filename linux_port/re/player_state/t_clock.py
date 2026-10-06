"""When does the fight-frame counter 0x8C475200 start advancing on each slot?"""
from harness import *
br = boot()
for s in (1, 2, 3):
    load(br, f"states/slot{s}.state"); prev = None; starts = []
    for t in range(900):
        br.emu.run(); v = struct.unpack_from("<I", br.ram, 0x475200)[0]
        if prev is not None and (v != prev) != (len(starts) % 2 == 1): starts.append(t)
        prev = v
        if t == 260: shot(br, os.path.join(HERE, f"shots/t_clock_slot{s}_260.png"))
    print(f"slot{s}: counter toggles (start/stop) at frames {starts[:8]}  final={prev}")
print("DONE"); sys.stdout.flush(); os._exit(0)
