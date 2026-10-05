"""E16: stage id. From menu_stage.state choose several stages (cursor moves), press A, run until
the fight-live counter 0x8C475200 advances, screenshot, keep a full-RAM snapshot in memory, save a
small match state per stage (stage_<k>.state). Then diff: bytes constant within each stage's two
snapshots (60 frames apart) and distinct across stages."""
from harness import *
br = boot()
moves = {"c0": [], "r": ["right"], "rr": ["right", "right"], "d": ["down"], "dd": ["down", "down"],
         "rd": ["right", "down"], "rdd": ["right", "down", "down"], "u": ["up"]}
snaps = {}
os.makedirs(os.path.join(HERE, "shots/e16"), exist_ok=True)
for name, mv in moves.items():
    load(br, os.path.join(LP, "menu_stage.state"))
    for m in mv: br.press(BTN[m], 2, player=0); br.press(0, 8, player=0)
    shot(br, os.path.join(HERE, f"shots/e16/{name}_sel.png"))
    br.press(BTN["a"], 2, player=0); br.press(0, 2, player=0)
    prev = u32(snap(br), 0x8C475200); started = None
    for t in range(3000):
        br.run_frames(1)
        v = u32(snap(br), 0x8C475200)
        if v != prev: started = t; break
        prev = v
    br.run_frames(30); a = snap(br); br.run_frames(60); b = snap(br)
    shot(br, os.path.join(HERE, f"shots/e16/{name}_fight.png"))
    with gzip.open(os.path.join(HERE, f"stage_{name}.state"), "wb") as fh: fh.write(br.emu.get_state())
    snaps[name] = (a, b)
    print(name, "fight started after", started, "frames; P1 pos", ppos(b, 0), "P2 pos", ppos(b, 1))
names = list(snaps)
ok = np.ones(len(snaps[names[0]][0]), bool)
for n in names: ok &= snaps[n][0] == snaps[n][1]
V = np.stack([snaps[n][0] for n in names])
nd = np.array([len(set(V[:, j].tolist())) for j in np.nonzero(ok)[0]]) if False else None
cand = np.nonzero(ok)[0]
sub = V[:, cand]
distinct = np.array([len(np.unique(sub[:, k])) for k in range(sub.shape[1])])
best = cand[(distinct >= len(names) - 1) & (sub.max(0) < 64)]
print("stage-id candidates (u8 const within stage, distinct across stages, <64):", len(best))
for j in best[:60]:
    print(f"  {0x8C000000+j:08X}", {n: int(V[i, j]) for i, n in enumerate(names)})
np.save(os.path.join(HERE, "tmp_e16_globals.npy"), V[:, 0x470000:0x480000])
print("DONE"); sys.stdout.flush(); os._exit(0)
