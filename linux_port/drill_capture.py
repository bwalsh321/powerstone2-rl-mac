"""drill_capture.py — harvest DAgger failure drills from the bot's own losses (Oct 3 2026; Blake: DAgger is the lever).

The bot plays the held-out lv8mix lineups (slots 90-94) exactly as in the battery (deterministic, base env, its own
action set). Every --every decisions the full emulator state is pushed into a ring buffer. When a round ends in a
LOSS, the snapshots taken ~--lead seconds before the end (default 8 and 4 s) are written as drills: the human then
replays those moments as the bot (drill_play.py) and his actions become corrections in the bot's own state
distribution — the DAgger idea, in the form a real-time fighting game allows.

  python drill_capture.py --model ./powerstone_v6_leg116_league.zip --losses 40 --instance 44 --out drills/leg116
Writes drills/<tag>/drill_NNN.state.gz (raw emulator state, gzip) + drill_NNN.json (slot, model, seconds before the
KO, round stats) + index.jsonl. A step is ~0.1 s of game time (6-10 frames).
"""
import argparse, collections, gzip, json, os
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--core", default=os.environ.get("PS2_CORE") or os.path.expanduser("~/cores/flycast_libretro.so"))
ap.add_argument("--game", default="../Power Stone 2 (USA).chd")
ap.add_argument("--slots", default="90,91,92,93,94")
ap.add_argument("--losses", type=int, default=40, help="stop after harvesting drills from this many lost rounds")
ap.add_argument("--max-episodes", type=int, default=200)
ap.add_argument("--every", type=int, default=10, help="snapshot every N decisions (~1 s)")
ap.add_argument("--lead", default="8,4", help="seconds before the KO to keep (comma list)")
ap.add_argument("--health", default="", help="instead of --lead: snapshot the moment the bot's health first drops below each of these fractions (e.g. 0.5,0.25), kept if the round is lost (Blake, Oct 4)")
ap.add_argument("--min-before", type=float, default=3.0, help="--health mode: drop a drill whose KO came less than this many seconds after the snapshot (one combo from the mark to dead = nothing to learn)")
ap.add_argument("--instance", type=int, default=44)
ap.add_argument("--out", required=True)
a = ap.parse_args()

from obs_stack import FrameStack, kd_for
from powerstone_env_libretro import PowerStoneEnvLibretro
from recurrent_policy import PolicyRunner, load_model

slots = [int(x) for x in a.slots.split(",")]
hp_marks = sorted({float(x) for x in a.health.split(",") if x.strip()}, reverse=True)
leads = sorted({float(x) for x in a.lead.split(",")}, reverse=True)
os.makedirs(a.out, exist_ok=True)
env = PowerStoneEnvLibretro(core_path=a.core, game_path=a.game, states_dir="./states", state_slots=slots,
                            instance_id=a.instance, bridge_dir=os.path.abspath(f"./bridge_probe_{a.instance}"))
model = load_model(a.model)
runner = PolicyRunner(model)
env.set_action_mode(int(model.action_space.n))
K, d = kd_for(model)
fs = FrameStack(K, d) if K > 1 else None
emu = env._lr_bridge.emu
STEP_S = 0.1
keep = int(max(leads) / (STEP_S * a.every)) + 2

n_drill = len([f for f in os.listdir(a.out) if f.endswith(".state.gz")])
index = open(os.path.join(a.out, "index.jsonl"), "a")
losses = eps = 0
while losses < a.losses and eps < a.max_episodes:
    env.STATE_SLOTS = [slots[eps % len(slots)]]
    obs = np.asarray(env.reset(), np.float32)[:d]; obs = fs.reset(obs) if fs else obs
    runner.reset()
    ring = collections.deque(maxlen=keep)
    t, done, info = 0, False, {}
    me = env.AGENT_PLAYER - 1
    hp_prev, hp_snaps = env.prev_health[me], {}
    while not done:
        if not hp_marks and t % a.every == 0:
            ring.append((t, emu.get_state()))
        act = runner.act(obs, deterministic=True)
        o2, r, done, info = env.step(int(act))
        hp = env.prev_health[me]
        for m in hp_marks:
            # first crossing from above; a round that starts below a mark has no drill for it
            if m not in hp_snaps and hp_prev >= m > hp > 0.001 and not done:
                hp_snaps[m] = (t + 1, emu.get_state(), round(hp, 3))
        hp_prev = hp
        o2 = np.asarray(o2, np.float32)[:d]; obs = fs.push(o2) if fs else o2
        t += 1
    eps += 1
    result = info.get("result", "timeout")
    if result != "loss":
        continue
    losses += 1
    slot = int(getattr(env, "_episode_slot", env.STATE_SLOTS[0]))
    picks = []
    if hp_marks:
        picks = [(tt, blob, dict(health_mark=m, health=h)) for m, (tt, blob, h) in sorted(hp_snaps.items(), reverse=True)
                 if (t - tt) * STEP_S >= a.min_before]
    for lead in ([] if hp_marks else leads):
        target = t - int(lead / STEP_S)
        cands = [(abs(tt - target), tt, blob) for tt, blob in ring if tt <= target + a.every // 2]
        if cands:
            _, tt, blob = min(cands, key=lambda c: c[0])
            picks.append((tt, blob, {}))
    for tt, blob, extra in picks:
        if not blob or len(blob) < 1_000_000:
            continue
        name = f"drill_{n_drill:03d}"
        with gzip.open(os.path.join(a.out, name + ".state.gz"), "wb") as fh:
            fh.write(blob)
        meta = dict(drill=name, model=os.path.basename(a.model), slot=slot, episode=eps, step=tt, end_step=t,
                    seconds_before_ko=round((t - tt) * STEP_S, 1), action_set=int(model.action_space.n),
                    ep_stats={k: (float(v) if isinstance(v, (int, float, np.floating)) else str(v))
                              for k, v in getattr(env, "_ep", {}).items()}, **extra)
        json.dump(meta, open(os.path.join(a.out, name + ".json"), "w"), indent=1)
        index.write(json.dumps(meta) + "\n"); index.flush()
        n_drill += 1
    print(f"[capture] episode {eps} slot{slot} LOSS at step {t}: drills so far {n_drill} (losses {losses})", flush=True)
print(f"[capture] done: {eps} episodes, {losses} losses, {n_drill} drills in {a.out}", flush=True)
