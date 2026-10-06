"""S13: stage-ID search. For each stage state take RAM at +10 f and +400 f. Candidate byte/word addresses: constant within
each stage, and pairwise-distinct across the 7 distinct stages (desert & desert_menu must AGREE; pharaoh separate)."""
from common import *
br = boot()
snaps = {}
for name, path in STAGE_STATES.items():
    load(br, path); br.run_frames(10); a = br.ram.copy(); br.run_frames(400); b = br.ram.copy()
    snaps[name] = (a, b)
names = list(STAGE_STATES)
stable = np.ones(len(br.ram), bool)
for a, b in snaps.values(): stable &= (a == b)
vals = np.stack([snaps[n][0] for n in names])          # [S, N] bytes
uniq_names = [n for n in names if n != "desert_menu"]
V = np.stack([snaps[n][0] for n in uniq_names])
agree = snaps["desert"][0] == snaps["desert_menu"][0]
# all distinct across the 8 unique stages
srt = np.sort(V, axis=0)
distinct = np.all(srt[1:] != srt[:-1], axis=0)
cand = np.nonzero(stable & agree & distinct & (np.max(V, 0) < 32))[0]
print("byte candidates (all distinct, <32):", len(cand))
for i in cand[:60]:
    print(f"  {0x8C000000+i:08X}: " + " ".join(f"{n}={int(snaps[n][0][i])}" for n in uniq_names))
# disk budget: keep only the two windows holding the stage-id cells
np.savez_compressed("data/s13_stage_id_windows.npz", **{n: snaps[n][0][0x46E000:0x473000] for n in names},
                    **{n + "_hi": snaps[n][0][0x542000:0x543000] for n in names})
for cell in (0x8C46E198, 0x8C472CF0, 0x8C472CF4, 0x8C472CF8, 0x8C54235E, 0x8C542363):
    print(f"  {cell:08X}: " + " ".join(f"{n}={int(snaps[n][0][cell & 0xFFFFFF])}" for n in names))
print("DONE")
