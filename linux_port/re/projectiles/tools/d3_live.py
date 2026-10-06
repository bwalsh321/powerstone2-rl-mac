"""Live smoke of proposed_ledger_threats.LedgerThreatScanner on a lineup state (instance 4)."""
import gzip, os, sys, time, numpy as np
from collections import Counter
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "re/projectiles"))
from flycast_bridge import FlycastBridge
from proposed_ledger_threats import LedgerThreatScanner, obs_block
core = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
br = FlycastBridge(core, os.path.join(ROOT, "../Power Stone 2 (USA).chd"), os.path.join(ROOT, "states"), instance_id=4)
br.run_frames(8); br.emu.set_state(gzip.open(sys.argv[1]).read()); br.run_frames(4)
sc = LedgerThreatScanner(bot_seat=1); kinds = Counter(); labels = Counter(); own = Counter(); mel = Counter(); dt = []
for f in range(int(sys.argv[2])):
    br.emu.run()
    if f % 3: continue
    t0 = time.perf_counter(); r = sc(br.ram, f); dt.append(time.perf_counter() - t0)
    for t in r["threats"]:
        kinds[t["kind"]] += 1; labels[t["label"] or hex(t["vt"])] += 1; own[t["own"]] += 1
    for m in r["melee"]:
        mel[m["seat"]] += m["active"]
    ob = obs_block(r, (0.0, 0.0, 0.0))
print("kinds", dict(kinds)); print("own flag", dict(own)); print("labels", labels.most_common(15))
print("melee-active sweeps per seat", dict(mel), f"scan cost median {1e3*np.median(dt):.2f} ms p99 {1e3*np.percentile(dt,99):.2f} ms; obs len {len(ob)}")
br.emu.close()
