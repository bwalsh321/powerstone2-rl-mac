# HANDOFF — Power Stone 2 RL, M2 MacBook port session (Aug 22–28, 2026)

## LEG 4 — THE SYNTHESIS LEG (Aug 31->Sep 1): NEW FRESH-LINEAGE CHAMPION

All-6-worker self-play vs pool_league (24 zips: rig checkpoints
0.2-31.9M incl. leg1's 28-31.9M snapshots + all program finals + seed),
warm start 3B, 2M steps (lineage lifetime now 4M), post-reboot, one
boot-flake retry absorbed by the new watchdog launcher (launch_leg4.sh
— the v2 wrapper kills teardown-hung crashes instead of waiting).

Training vs the league: q1-q4 29.8/29.5/20.0/22.8%%, ep len 490->943 —
win%% held ~25%% against MIXED opposition whose strong half is the
31.9M lineage, fights lengthening as its own snapshots entered.
(Blake's calibration note, Sep 1: leg1's 31.9M "peaked around 15-20M"
— the middle was the reward-era plateau; effective-step gap vs the
fresh line is ~4-5x, not 16x, and the last 4M selfplay burst did the
rest.)

BATTERY (n=50 det / n=12 A/B):
- slot3 (lv8): 0.0 / 1.20 / 0.06 — the wall is now 5-0 vs fresh legs.
- slot2 (lv3): **42.0 / 6.74 / 1.56 — new fresh-lineage record**
  (3B: 40.0/6.26/1.28), earned against honest opposition.
- **A/B vs 3B (its warm start): 8W-1L-3T — decisively outgrew its
  parent in one leg.**
- A/B vs leg1: 1W-11L (3B read 4-8; n=12 noise + intransitivity —
  the league diet tuned it vs fresh-lineage styles; slot2 is the
  truer transfer measure and it leads there).

VERDICT: the synthesis works — deep pool + full self-play budget beat
both its parent and every program leg on transfer, in 2M steps. THIS
is the leg shape to redline on the 7950X (Blake: "found the most
scalable leg to run — red line it and let it cook"). Lineage seat:
powerstone_v6_leg4_league.zip is the fresh-line champion;
powerstone_v6_ppo.zip (leg1) remains overall champion, NOT overwritten.
Next: keep compounding this lineage (leg 5 = same recipe warm-started
from leg4, pool grows), Linux-box bring-up (repo push pending Blake),
recorder/DAgger port, reddit video of leg1 still unrecorded.

## PRE-REGISTERED INTERVENTION PLAN (Blake + session, Sep 3 — binding until amended by Blake)

The league diet stays PURE self-play. Blake's pushback, ratified: the
curve is climbing, and this project's history says interventions
without a measured failure are how legs get burned (reward era 0-for-5;
leg 3C's dead COM stream; Law 5). Pure self-play keeps paying for
things it never trained on (leg1's FFA jump; the current slot3
behavior climb). NO diet change on a forecast — soft-pool worry
included.

**TRIGGER (must actually fire before any diet change):** slot2 flat or
down for TWO consecutive leg batteries, OR slot3 behavior metrics
(picks+forms) stalling across two legs. Current references at
registration: slot2 84.0 (leg 9); slot3 picks 3.42 / forms 0.48 and
climbing.

**RESPONSE WHEN FIRED (in order, nothing skipped):**
1. MEASUREMENT FIRST: stamp lv6-FFA and lv8-1v1 states (headless via
   menu_drive; ORIGINAL mode; difficulty via options; spare emu
   instance so the relay is untouched) and run them as EVAL-ONLY
   discriminators — zero training budget spent.
2. Only then, give ONE worker to the highest rung the model already
   wins >=20%% of at eval (Law 1: winnable rungs only; Law 5: never a
   dead stream). Everything else stays league self-play.
3. Graduation: rung moves up when its training stream sustains ~60%%.
Anyone (human or session) proposing a diet change before the trigger
fires must be pointed at this section.

## LEAGUE LEGS (running record — one line per leg; relay automated Sep 1)

Recipe per leg: league_leg.sh / league_battery.sh, 2M steps, full
self-play vs pool_league (self-growing), warm start = previous leg,
battery + auto-launch chained. Lineage: bc256 -> 3B -> leg4 -> leg5...

| leg | lifetime | train q1-q4 vs league | slot3 | slot2 | A/B vs prev | vs leg1 |
|-----|----------|----------------------|-------|-------|-------------|---------|
| 4 | 4M | 29.8/29.5/20.0/22.8 | 0.0 | 42.0/6.74/1.56 | 8-1-3 (3B) | 1-11 |
| 5 | 6M | 38.3/28.0/47.2/52.1 | 0.0 | **50.0/7.02/1.52** | **11-1** | **6-6** |
| 6 | 8M | 55.8 -> 67.0 (halves) | 0.0 (picks 1.46, forms 0.18 — first life) | **64.0/7.86/1.92** | **11-1** | 7-5 (n=12; see 50-ep below) |
| 7 | 10M | 62.5/75.6/73.7/78.6 | 0.0 (1.34/0.08) | **78.0/9.04/2.70** | 9-3 | — |

| 8 | 12M (CLEAN league) | 84.8 -> 90.2 | 0.0 (**picks 2.40, forms 0.22 — doubling leg-over-leg**) | **82.0/9.56/2.74** | 11-1 | 7-5 (n=12) |

**LEG 8 (Sep 3, first clean-league leg): THE CURVE HOLDS.** slot2
40->42->50->64->78->**82** under the honest opponent mix — the skew was
not the engine. Picks 9.56 vs leg1's 9.76: component parity. slot3
still 0 wins but its behavior metrics are now climbing leg-over-leg
(1.34/0.08 -> 2.40/0.22). NEW LEAGUE DYNAMIC to watch: with mtime
sorting, "recent 10" = mostly its OWN latest snapshots once it's the
strongest line in the pool — training win%% jumped to ~87%% (soft again,
the 3B problem at a higher level). The lineage has outgrown its league;
options for a future boundary: raise recent_k, weight prog_*/leg1
zips, or PFSP-by-winrate sampling. Not changed mid-relay.**

| 9 | 14M | 78.5 -> ~84 flat | 0.0 (**picks 3.42, forms 0.48 — third straight climb**) | **84.0/10.02/3.06 — picks+forms EXCEED leg1** | 11-1 | 8-4 (n=12) |

**LEG 9 (Sep 3): component parity PASSED.** slot2 picks 10.02 and
forms 3.06 now exceed leg1's 9.76/3.00; win%% 84 vs 98 — the remaining
gap is pure win-conversion. slot2 slope moderating (78->82->84):
either the lv3 asymptote or the soft pool capping growth (training
win%% ~84 sustained, below the 92 flag line). The live frontier is
slot3's behavior climb: 1.34/0.08 -> 2.40/0.22 -> **3.42/0.48** over
three legs with zero wins — the wall's base is eroding measurably;
first lv8 wins plausibly within a couple legs at this rate.**

| 10 | 16M | ~85 vs league | **2.0 — FIRST LV8 WIN EVER (1W/49L)**, picks 3.88, forms 0.54 | **86.0/10.76/3.18** | 9-3 | 8-4 (n=12) |

**LEG 10 (Sep 3): THE WALL CRACKED.** First lv8 eval win in project
history — after nine legs and 0-for-450, exactly as the three-leg
behavior climb (picks 1.34->2.40->3.42->3.88, forms 0.08->0.22->
0.48->0.54) predicted. One win in fifty is a crack, not a breach —
but it arrived on schedule, from pure self-play generalization, with
zero lv8 training data, on a laptop. slot2 86.0 still climbing (no
stall; pre-registration trigger NOT armed). The 7950X arrives to a
lineage that has now scored on everything the game has.**

| 11 | 18M | — | 0.0 (picks 3.22, forms 0.54 — climb PAUSED) | **90.0/10.42/3.12** | 8-4 | **9-3** (n=12) |

**LEG 11 (Sep 4): crack NOT consolidated** — 0/50 at lv8; leg 10's 1/50
stands alone for now (noise vs leading-edge unresolved; behavior
metrics paused their three-leg climb). Meanwhile slot2 hit **90.0**,
eight points from leg1's 98, and the quick probe read 9-3 — the best
yet. Trigger unarmed (86 -> 90).**

| 12 | 20M | — | **4.0 (2W/48L) — CRACK CONSOLIDATED**, picks 3.78, forms 0.62 | 88.0/10.60/3.20 | **10-2** | **11-1** (n=12, record) |

**LEG 12 (Sep 4): TWO lv8 wins — the crack is real.** After leg 11's
0/50 scare, leg 12 scored 2W/48L at lv8 with behavior metrics resuming
their climb (picks 3.78, forms 0.62 — both lineage records). Wins at
lv8 across three legs: 1, 0, 2 — a noisy leading edge, exactly what a
wall eroding from underneath looks like. Both AB probes set records:
10-2 vs its parent, **11-1 vs the leg1 champion** (n=12; the n=50
crown probe remains 29-21). slot2 read 88.0 (down 2 from 90 — inside
n=50 noise, but by the pre-registration letter this is one flat/down
leg: trigger is now ARMED; a second consecutive flat/down leg fires
it and the response is eval discriminators FIRST, no diet change).
OPS NOTE: leg 12's trainer hung in teardown AFTER printing "leg
complete" (mutex hang on clean exit — new variant of the known
failure mode); the hung main + 6 workers squatted CPU for ~50 min
until manually killed, and the stale ps2train tmux session would have
blocked leg 13's auto-launch. Relay procedure updated: after each leg,
verify trainer exit + session cleanup before battery. Consider adding
os._exit(0) after the final save in train_selfplay.py as a permanent
guard.**

## MIGRATION TO THE 7950X LINUX BOX (Sep 4, 2026)

Blake called the M2 era done: relay STOPPED mid-leg-13 (1,277 eps in,
progress discarded by design; league_state.txt intact at "13
./powerstone_v6_leg12_league.zip", so leg 13 = first Linux leg). Final
M2-era standings: leg 12, 20M lifetime, slot2 88.0, lv8 2W/48L, 11-1
(n=12) vs leg1. PRE-REGISTRATION TRIGGER REMAINS ARMED (90 -> 88).

Bring-up vehicle: this repo + linux_port/LINUX_BRINGUP.md +
linux_port/setup_linux.sh. Non-repo payload rsyncs from the Mac (CHD,
pool_league, states, demos*, model zips, league_state.txt). Gates
G1-G5 in LINUX_BRINGUP.md; G4 (50-ep slot2 parity vs the leg 12 Mac
numbers) is mandatory before any training — cross-platform obs parity
is where this project has been burned before (chest-obs law).
league_leg.sh / league_battery.sh made platform-aware (core path,
caffeinate, cd-to-script-dir). Open questions for the Linux era:
worker count (try 12 at G5; M2 ran 6), stagger (Metal race is
macOS-only), and whether the teardown hang follows us off macOS.

**CROWN PROBE AT n=50 (Sep 2, leg6 vs leg1): 29-21 (58%%).** 95%% CI
~44-71 — "at least even, probably ahead," NOT proof of dominance; the
training-state caveat still applies. The held-out slot2 curve is the
stronger witness: 40 -> 42 -> 50 -> 64 -> 78 vs leg1's 98, with picks
9.04 (leg1: 9.76) and forms 2.70 (3.00) nearly closed at 10M vs 31.9M
lifetime. slot3 wall: 7-0. **LEG 8 = FIRST CLEAN-LEAGUE LEG** (mtime
sort + tagged snapshots + leg4 backfilled active) — its numbers are
the first honest read of the recipe; treat any curve kink as
information about the old skew, not regression.**

**SEP 2 EXTERNAL REVIEW (fresh-model audit, verified against code+logs
— four findings CONFIRMED, all patched at the leg 7/8 boundary):**
1. OpponentPool sorted by filename step-number -> "recent 10" was
   permanently leg1's 27.9-31.9M snapshots (~56-66%% of episodes);
   prog_* finals/seeds parsed as 0 and were buried. FIXED: mtime sort.
2. PS2_FRESH reset the snapshot clock -> cross-leg name collisions;
   each leg overwrote its predecessor's pool snapshots. FIXED: leg-
   tagged names. 3. prog_leg4 never entered the pool (battery predated
   the cp line). FIXED: backfill in league_battery. 4. AB retry guards
   missing in league_battery. FIXED.
**INTERPRETATION CORRECTION for legs 5-6:** the lineage trained mostly
AGAINST leg1's late snapshots ON the same slot1 state the A/B probes
use — so "6-6"/"7-5 vs leg1" reads closer to "learned to beat leg1
where it practiced against leg1" than "caught the champion," and n=12
carries wide error bars (95%% CI on 6/12 is roughly 25-75%%). THE CLEAN
CLAIM is the held-out slot2 FFA curve at n=50: 40 -> 42 -> 50 -> 64 vs
leg1's 98 — real, accelerating transfer, different state, different
opponents. A 50-ep A/B vs leg1 is queued to settle the crown properly.
CANDIDATE LAW 9: an A/B on the training state is not a held-out test.
Also queued: a 1v1-lv8 discriminator state (the wall may be partly an
FFA wall — the lineage has only ever fought 1v1; slot3 is 3-opponent
FFA — two jumps at once, and a lv8 1v1 state is stampable headlessly
via menu_drive ORIGINAL mode with two seats NO ENTRY).

**LEG 6 (Sep 2 ~06:30Z): the crown probe (READ WITH THE CORRECTION ABOVE).** First
head-to-head WIN over the 31.9M champion (7-5, n=12 stochastic) at 8M
lifetime; slot2 40->42->50->64; beat leg 5 11-1; slot3 still 0 wins
but behavior stirring (picks 1.46, forms 0.18 vs leg5's 1.20/0.04).
Boot took 3 wrapper attempts (flake tax), ran clean after. PROMOTION
NOT DONE — powerstone_v6_ppo.zip untouched per standing rule; Blake's
call. (Note for that call: n=12 is thin for a coronation — a 50-ep
A/B or a slot2 gap-close would make it solid; leg 7 running.)

**LEG 5 (Sep 1): the lineage CAUGHT the champion.** slot2 compounding
40 -> 42 -> 50; beat its parent 11-1; **DEAD EVEN 6-6 vs leg1's 31.9M**
at 6M lifetime steps — the effective-step thesis validated in two days
of M2 time. Training curve dipped q2 (its own leg-4 snapshots entered
the pool) then punched to 52%%. slot3 still 0.0 (wall 6-0 vs fresh
legs). Leg 6 auto-launched, running.

## LEG-3 PROGRAM CLOSE-OUT (Aug 31 ~11:00Z) — FINAL FOUR-WAY TABLE

All legs 2M steps from fresh seeds; batteries n=50 deterministic
(slot3 lv8 FFA / slot2 lv3 FFA), A/B n=12 stochastic.

| leg | seed | diet | train trajectory | slot3 | slot2 | A/B vs seed | vs leg1 | cross-leg |
|-----|------|------|-----------------|-------|-------|------------|---------|-----------|
| 3A | bc256 | lv8 only | 0 -> 0.3%% | 0.0 / 1.20 / 0.04 | 14.0 / 5.02 / 0.74 | 10-2 | 0-12 | lost 1-11 to 3B |
| 3B | bc256 | self-play (shallow pool) | 88 -> 96%% vs pool | 0.0 / 0.88 / 0.00 | **40.0 / 6.26 / 1.28** | **12-0** | **4-8** | beat 3A 11-1, 3D 8-4, 3C 8-4 |
| 3C | bc256 | mix 4 lv8 + 2 self-play (DEEP pool = 3B lineage) | COM flat 0.1%%; SP 14.7->54.3%% | 0.0 / 1.16 / 0.02 | 14.0 / 3.36 / 0.42 | 11-1 | 2-10 | lost 4-8 to 3B |
| 3D | bclv8_256 (Blake's 23-1 corpus) | lv8 only | 0 -> 0.34%% | 0.0 / 1.28 / 0.08 | 28.0 / 3.86 / 0.62 | 7-5 | 1-11 | lost 4-8 to 3B |
| refs | leg1 (31.9M selfplay) | — | — | 15.0 / 4.00 / 0.95 | 98.0 / 9.76 / 3.00 | — | — | — |
| | leg2 (warm+lv8) | — | flat 10%% | 4.0 / 4.72 / 0.76 | 88.0 / 8.92 / 2.54 | — | 3-9 | — |

**WINNER: 3B (self-play), by every transferable measure** — best slot2
(40.0, ~3x any other fresh leg), only fresh leg competitive with leg1
(4-8), crushed its own seed 12-0, and beat every sibling head-to-head.

**WHY (what the data says):**
1. **Gradient continuity is the engine.** The two legs whose win-signal
   never dried up (3B always-winnable pool; 3C's self-play stream) are
   the only two that LEARNED to win anything. The three lv8-only diets
   (leg2 warm, 3A, 3D) produced flat ~0-10%% trajectories: exposure to
   losses is not information about winning.
2. **The lv8 wall stands 4-0.** No fresh leg scored a single slot3 win
   at n=50. Only leg1's 31.9M-step lineage wins there (15%%).
3. **BC seeds don't transfer wins (3D).** Blake's validated 23-1 corpus
   at 80.6%% val acc produced 8 training wins in 4,653 eps and a 7-5
   A/B vs its own seed (RL had nothing to amplify). Textbook covariate
   shift: no recovery demonstrations off Blake's manifold. This is the
   program's cleanest negative and the DAgger mandate.
4. **3C's split verdict:** its self-play stream vs the DEEP pool (3B's
   lineage, via the shared pool dir — accidental league training) was
   the program's best climb (14.7->54.3%%), but with only 2/6 workers
   on self-play (465 eps vs 3B's 3,126) and 2/3 of its gradient spent
   on dead lv8 losses, it transferred worst (slot2 14.0) and lost the
   head-to-head 4-8. Opposition quality was right; the gradient BUDGET
   was wrong.

**RECOMMENDED NEXT MOVES (in order):**
1. **Deep-pool full self-play leg** — 3B's diet with 3C's opposition:
   all 6 workers self-play, pool seeded with ALL program zips + leg1 +
   old opponent_pool (the real league). Warm start 3B. This is the
   synthesis the data asks for.
2. **DAgger/recorder libretro port** — the only route by which Blake's
   play can enter effectively (relabel the POLICY's states, not
   Blake's). Prereq for any future demo work; rig recorder is the
   reference.
3. Consider extending 3B +2M as the cheap control for (1).
4. Launcher hardening: retry-on-EOFError wrapper (the Metal boot race
   killed two chained launches).
Housekeeping: nothing promoted — powerstone_v6_ppo.zip is still
selfplay_leg1, the undisputed overall champion. Only the claudebridge
tmux remains; compute idle.

## THE LEG-3 PROGRAM (Blake's spec, Aug 29 evening) — three legs, one seed, pick the winner

All three legs start from the SAME fresh seed — powerstone_v6_bc256.zip
([256,256], BC on demos:3 + demos_v4corpus, 83.1%% val on the rig) — so
the training DIET is the only variable. **2M steps each (~7h — Blake's
call, Aug 29: leg2 was flat after 1M and the rig's P/Q/R comparison
legs were 1M; slope is readable at 2M and the winner gets EXTENDED by
resuming its final zip on the same diet),** same battery after each (slot3 50-ep, slot2 50-ep, A/B vs the
bc256 seed and vs selfplay_leg1). Compare, figure out which is best AND
WHY. Blake records new demos of his own play sometime during the
program (needs the recorder's libretro port first — record_demo.py is
lua-era).

- **Leg 3A — lv8 only** (launches automatically after the Aug 29
  checkpoint sweep): `PS2_WARM=./powerstone_v6_bc256.zip PS2_FRESH=1
  train_com.py`, STATE_SLOTS=[3]. Log train_leg3a_out.txt,
  checkpoints_lv8_fresh/.
- **Leg 3B — 1v1 self-play vs its prior self**: `train_selfplay.py`
  with PS2_WARM=bc256, PS2_FRESH=1, PS2_POOL=./pool_bc256 (seeded with
  ONLY the bc256 zip; snapshots of itself accumulate). slot1.
**LEG 3A COMPLETE (Aug 30 04:44Z, 2M steps, powerstone_v6_bc256_lv8leg
.zip). Training stream: DEMOLISHED — q1-q4 win 0.0/0.0/0.3/0.2%%, picks
0.58->1.11 (doubled, but tiny), forms ~0.05, len 389->441, zero
timeouts. The fresh seed vs lv8 is the sparse-signal regime: with ~0%%
wins there is no win-gradient to climb, only dense shaping moved.
Echoes rig P/Q/R (fresh lineage weak in absolute terms). **BATTERY (Aug 30 07:00Z, n=50 det + n=12 A/B): slot3 0.0%%
(0W/50L)/1.20/0.04 — flatlined vs lv8; slot2 14.0%%/5.02/0.74 (leg1:
98.0); A/B vs its OWN SEED 10W/2L — the RL leg genuinely improved the
policy (the raw bc256 seed loses 2-10 to its trained child); A/B vs
leg1 0W/12L. READING: real learning, wrong altitude — lv8-only cannot
bootstrap wins from a fresh seed (0%% train wins = no win-gradient);
the improvement all came from dense shaping. 3B (self-play) is the
regime where the fresh seed can actually WIN half its episodes by
construction — the interesting comparison.**
The lv8-BC seed bake ALSO done: powerstone_v6_bclv8_256.zip (val curve
in bake_lv8_out.txt) — leg 3D's seat is ready.**

- **Leg 3D — fresh lv8-BC seed on the lv8 diet (ADDED Aug 30, PRE-APPROVED
  by Blake: launch after 3C's battery, no further ask needed).** Blake
  recorded a NEW human corpus on the rig overnight: demos_lv8/demo_005.npz,
  11,704 pairs, 24 eps, **23-1 vs THREE lv8 COMs** across three re-stamped
  rig lv8 states (see README_MIGRATION3.md in ~/Downloads/macbook_migration3
  for provenance + the rig-side SLOT_META note — do NOT copy the rig env
  over the Mac's). Old pre-lv8 sittings quarantined rig-side. Seed bake
  RUNNING (tmux ps2bake, nice'd, log bake_lv8_out.txt):
  `bc_pretrain_lv8.py demos:1,demos_lv8:5,demos_v4corpus --arch 256x256`
  -> **powerstone_v6_bclv8_256.zip** (distinct name — NEVER overwrite
  powerstone_v6_bc256.zip mid-program, legs A/B/C warm-start from it).
  Ratio rationale (Blake's call): the old 9,943 human pairs CANNOT be
  validated as lv8 play (recorded vs the lv2-3 ladder) -> demoted to 1x
  texture; the validated lv8 slayer rides at 5x (~19%% of volume); more
  Blake sittings stack into demos_lv8/. Leg 3D = launch_leg3a.sh pattern
  with PS2_WARM=./powerstone_v6_bclv8_256.zip PS2_FRESH=1, log
  train_leg3d_out.txt, 2M steps (launch_leg3d.sh, WRITTEN). **ORDER
  SWAP (Blake, Aug 30 morning): 3D runs BEFORE 3C — it's the
  breakthrough candidate. Sequence: 3B battery -> 3D -> 3D battery ->
  3C -> final four-way table. THE SIGNAL TO WATCH on 3D's stream:
  nonzero training wins in q1 where 3A had 0.0%% — that's the
  prior->gradient link working.** **3D vs 3A isolates exactly what the
  new human data is worth** — same diet, same arch, only the seed differs.
**LEG 3B COMPLETE (Aug 30 ~13:40Z, 2M steps, powerstone_v6_bc256_spleg
.zip). Training curve vs its own pool: q1-q4 win 88.0/92.6/93.9/95.8%%,
picks 3.81->5.68 (q4 5.26), forms 1.39->2.13, len ~660 (q4 543 — wins
coming faster). CAVEAT: the pool started as ONLY the bc256 seed, so
88%% in q1 means it outgrew its infant self almost immediately; the
pool never supplied real pressure. Forms >2/ep is the standout —
self-play taught the transform game (3A managed 0.05). Battery running
(tmux ps2battery3b) -> chains LEG 3D launch (order swap, Blake's
call). Results appended when in.**

**3B BATTERY (Aug 30 16:15Z): slot3 0.0%%/0.88/0.00 (no lv8 transfer);
slot2 40.0%%/6.26/1.28 (vs 3A's 14.0 — self-play built REAL fighting
skill); A/B: 12-0 vs its seed, 11-1 vs 3A, 4-8 vs leg1 — a 2M-step
fresh line taking 1/3 of games off the 31.9M champion. 3B IS THE
PROGRAM LEADER.**

**3D FIRST SIGNAL (Aug 30 16:15Z): 0 WINS IN 856 EPISODES** (picks
0.97, forms 0.04 — 3A's profile). Seed verified correct
(bclv8_256, bake val_acc 80.6%%; weak spots: jump 49.9%%, grab 27.5%%,
throw 0%%). **The lv8-BC seed did NOT transfer Blake's wins — the
prior->gradient hypothesis is DENTED at the entry link.** Leading
explanation (textbook + matches rig Sec-22 history): BC covariate
shift — the clone leaves Blake's state manifold within seconds and has
zero recovery demonstrations; per-frame mimicry (80%%) is not
closed-loop skill. This STRENGTHENS the rig's standing DAgger
recommendation (relabel the CURRENT policy's states) and 3B's
self-play result: gradient continuity beats demonstration priors on
this problem so far. 3D runs to completion anyway (its battery may
still show slot2 gains); 3C (mix) after.**

**3D COMPLETE (Aug 30 23:30Z, powerstone_v6_bclv8_256_lv8leg.zip):
8 wins in 4,653 episodes. q1-q4: 0.00/0.26/0.09/0.34%%, picks ~1.17,
forms ~0.06. NO late emergence — the lv8-BC seed never bootstrapped;
the first-signal verdict stands at full-leg scale. **3D BATTERY (Aug 31 00:55Z):
slot3 0.0%%/1.28/0.08; slot2 28.0%%/3.86/0.62; A/B vs its seed only
7W/5L (3A went 10-2 over ITS seed — a never-winning policy generates
no lessons for RL to amplify); vs leg1 1-11; vs 3B 4-8. The chained 3C
launch died at boot (EOFError, the Metal race — 2nd chain casualty);
caught by Blake ~01:00Z, relaunched clean on retry: 6/6 bridges, BOTH
stream types verified (slot3 COM eps + slot1 self-play eps with [opp]
pool lines). TODO next session: retry-on-EOFError wrapper in the
launcher scripts. Final four-way close-out lands with 3C's battery
(~09:00Z Aug 31).**

- **Leg 3C — the mix**: `train_mixed.py` NEW — 4 workers lv8 COM FFA
  (slot3) + 2 workers self-play 1v1 (slot1), one learner; net
  distinguishes contexts via stage one-hot + DIFF_DIM.

**HISTORICAL CONTEXT (rig HANDOFF, Aug 23-26 — read before judging
these legs):** the 256/bc lineage already ran three curriculum legs on
the rig (P/Q/R, 3.7M lifetime steps): lv4 bake-off 11.2 / 11.2 / 13.8
vs legM's ~66, picks PINNED at 2.83-2.85 all three tables, one real
climb (lv2 22->38%% in Q) then plateau (R). Verdict recorded there:
rewards/capacity/curriculum all eliminated — "the policy plateaus in
states no demonstration covers"; standing recommendation was a DAgger
pass (teacher relabels the CURRENT policy's states). SO: expect leg-3
absolute numbers to start far below the leg1 lineage; judge on SLOPE
across the leg (the rig's own rule), and know that P/Q/R never saw
lv8 data, never saw self-play, and never ran the mix — those are
exactly the three variables this program isolates. If all three
plateau the same way, the rig's DAgger diagnosis stands confirmed and
the priority becomes the recorder port + new demos (Blake vs lv8 /
DAgger relabeling), not more legs.

## LEG 2 — THE LV8 LEG (launched Aug 28 ~23:09, Cowork session + Blake)

**LEG 2 RESULT (Aug 29): the warm-start lv8 repeat DID NOT WORK.**
4.00M steps (31.918M -> 35.921M), 8,300 episodes, 0 crashes, 0 timeouts
(no coward signature — the -2 loss scale did its job; ep len stable
~450-500). Training stream (stochastic) plateaued after ~1M steps:
q1 8.0% win / 4.34 picks / 0.77 forms -> q2-q4 flat at ~10% / ~4.9 /
~0.92. Deterministic slot3 evals: leg1 baseline 15.0/4.00/0.95 (n=50);
leg2 FINAL 4.0/4.72/0.76 (n=50) — BELOW baseline; mid-leg 34.4M
checkpoint 15.0/5.80/1.15 (n=20) — the best artifact of the leg.
Entropy stable all leg (0.52-0.57) -> the final-zip drop is PPO churn /
"peaked then eroded" (rig HANDOFF Sec 22 redux), not entropy collapse.
Checkpoint sweep (4 zips spanning the leg, n=50 slot3) queued to find
the true peak; slot2 + A/B battery (Aug 29 19:00Z): **slot2 88.0%%
(44W/6L) / 8.92 picks / 2.54 forms — vs leg1's 98.0/9.76/3.00: MILD
EROSION of the lv3 benchmark (still above the Windows band), and A/B
head-to-head leg2-final vs leg1: 3W/9L — leg1 wins.** The lv8-only
diet cost a little of everything and bought nothing measurable in the
final zip. **CHECKPOINT SWEEP (Aug 29 21:00Z, n=50 slot3 deterministic):
32.4M 8.0/4.90/0.88 | 33.2M 16.0/4.40/0.86 | 34.4M 10.0/5.22/0.94 |
35.4M 12.0/5.18/1.08 | final 35.9M 4.0/4.72/0.76 | leg1 baseline
15.0/4.00/0.95. Reading: win%% bounces 4-16 across checkpoints — churn
noise, no checkpoint CLEARLY beats leg1 (peak 33.2M @ 16.0 is within
noise of 15.0); picks/forms mildly above leg1 late-leg. The earlier
mid-leg 15.0 (n=20) was noise, not a peak. NO PROMOTION — leg2 is a
clean negative result, full stop.**
**LEG 3A LAUNCH (Aug 29 ~21:08Z, tmux ps2train, log
train_leg3a_out.txt): took FOUR attempts — the 6s worker-boot stagger
let the macOS Metal-init race kill a spawning worker 3x in a row
(silent worker death right after REIOS boot -> SubprocVecEnv EOFError;
SDLARCH_LOG=1 diagnosed it). FIX: stagger raised 6s -> 20s in ALL
THREE trainers; 6/6 workers then booted clean. Also NEW
launch_leg3a.sh — nested-tmux quoting ate the first auto-launch; leg
launches are launcher SCRIPTS from now on. Health at +4 min: episodes
streaming, contested (2.6-3.3 bars dealt), all losses so far (expected
— fresh bc256 seed vs lv8), 0 tracebacks. 2M steps, ETA ~04:30Z.** NOTHING PROMOTED: powerstone_v6_ppo.zip is still selfplay_leg1.

**VERDICT (Blake, Aug 29): BIL's actual prescription was a FRESH run on
lv8, not warm-starting the 31.9M model — those weights are well trained
on beating weak COMs, and 4M steps of 90%-loss lv8 data couldn't pull
them off that prior. Next experiment: FRESH net (+BC pretrain) -> RL on
lv8.** Which needs kit #4:

**KIT #4 INVENTORY (Aug 29 repo audit — most of it is ALREADY in the
GitHub repo):** bc_pretrain.py, bc_rehearsal.py, record_demo.py,
record_gamenight.py, cheater_bot.py (the scripted-aimbot demonstrator —
"the cheater teaches aim, the family teaches everything else"),
aimbot_gauntlet.py, BC seed zips (powerstone_v6_bc.zip / bc256), and the
FULL rig docs/HANDOFF.md (Secs 20/22/25.4/29/35). **MISSING = the demo
corpora, rig-only (allowlist .gitignore publishes only one sample npz
each): demos/ (Blake's play, 9,943 pairs), demos_cheater/ (the aimbot
farm — the bulk of the 252k-pair rehearsal set), demos_humans/ if game
night ever recorded. MOVE THOSE from the 12700K to the Mac.**
**KIT #4 ARRIVED (Aug 29 evening, ~/Downloads/kit4 -> linux_port/) with
two corrections (KIT4_NOTES.md): the rehearsal set is demos/ (9,943,
Blake) + demos_v4corpus/ (247,828, cheater_bot v4 discrete ladder) —
demos_cheater/ is OLDER analog-era recordings, inspect action
histograms before ever feeding to BC; and demos_humans/ does not exist
(game night ran without --record), so Blake-vs-strong-opponents data
still needs a future recording session. bc_pretrain.py, bc_rehearsal.py,
powerstone_v6_bc256.zip + bc.zip pulled from the repo into linux_port/.
VERIFIED on the Mac venv: both corpora load (obs dim 122), bc256 loads
CPU + predicts, arch [256,256]. train_com.py now takes PS2_WARM=<zip>
and PS2_FRESH=1 for the fresh-lineage leg 3: warm start bc256, fresh
timeline, checkpoints_lv8_fresh/.** Note the
recorders are lua-era (free-running emulator) — they need the standard
libretro port before NEW demos (e.g. Blake vs lv8) can be recorded on
the Mac. Rig HANDOFF already reached the same conclusion as BIL:
"lv5 needs a PRIOR. Priority: game night / human demos > aimbot demo
farm > more reward work" (Sec 30/35 era).

BIL consult (Blake's brother-in-law, ML engineer at Epic): the rig-era
curriculum stalled at COM lv5 because the stream was dominated by easy
wins — skip the ladder, train straight into max difficulty. This leg is
that experiment, pure (self-play returns NEXT leg; alternate at the leg
level — Blake's call, per-episode mixing not built).

- **slot3.state NEW (Blake-stamped via make_savestates):** ORIGINAL mode
  true-FFA, desert, COM DIFFICULTY 8 (options menu), P1 Pride / P2
  FALCON human / P3 Ryoma / P4 Accel, colors distinct (same color =
  team battle — avoid). Verified: 4x1000 healths after intro, P2
  face_norm 0.992. NOTE: menu navigation is fully scriptable headless
  — menu_drive.py walked options/player-select this session (COM toggle
  = A on HUMAN row; colors cycle R->Y->B->G; A on PLAYER SELECT row
  picks the SHOWN character — cycling mechanism still unknown, human
  was faster).
- **Env changes (powerstone_env_v6.py):** SLOT_META[3] REDEFINED ->
  (2, 8) (desert dim, lv8; DIFF_DIM now reads 1.0 — first time the net
  sees it); LOSS_SCALE_BY_LEVEL[8] = 0.2 (effective terminal loss -2;
  gamma-.999 coward math: delaying -10 to ep end 'saves' ~7 vs -2.4
  stall bleed — cowering paid; at -2 it strictly loses); gem neg floor
  1.5 at lv>=8 (keeps dying the worst outcome).
- **train_com.py NEW:** plain PowerStoneEnvLibretro vs-COM trainer,
  train_selfplay skeleton minus pool, STATE_SLOTS=[3], warm start
  MANDATORY (= powerstone_v6_ppo.zip = selfplay_leg1), checkpoints_lv8/,
  4M steps.
- **BASELINE (baseline_lv8_out.txt): leg1 vs slot3, 20 eps
  deterministic: win 15.0% (3W/17L), picks 4.00, forms 0.95** — vs
  98%/9.76/3.00 on slot2 lv3. Hard but winnable = real gradient.
- **Launch health (first ~3 min):** 6 workers, all episodes contested
  (dmg 1.7-6.4 bars out, stones picked, first wins + 3-form episode in
  the stream), ~73 fps aggregate climbing, timesteps continue from
  31.918M, zero tracebacks. tmux `ps2train`, caffeinate, log
  train_leg_lv8_out.txt. Reattach: `tmux attach -t ps2train`.
- **Morning protocol:** check tail of train_leg_lv8_out.txt for [ep]
  win trend + tracebacks; eval latest checkpoints_lv8 zip on slot3
  (eval_parity --slot 3, compare to the 15% baseline) AND on slot2 +
  A/B vs leg1 (did lv8-only data erode the old skills? informative
  either way — leg1 zip preserved).
- **Claude command bridge NEW (this session):** claude_bridge_watcher.sh
  in linux_port, tmux `claudebridge` — Cowork's device shell can't run
  the emulator (isolated VM), so commands go through
  claude_bridge/cmd.sh -> out.txt on the mounted folder. Kill when
  done: `tmux kill-session -t claudebridge`.
- Deferred: BC/DAgger kit (demos + scripts) still rig-side — "kit #4"
  — needed before the fresh-net + BC-pretrain lv8 variant. The aimbot
  DAgger naming/history lives in rig HANDOFF Sec 22.

## NEXT SESSION BRIEF (Claude Code, cwd = macbook_migration/) — Aug 28

Immediate mission while the 7950X ships: first real training leg on
the M2. Protocol, in order:

1. **Warm-start audition: DONE (Aug 28) — legG KEEPS the seat.**
   legM_final, eval_parity 20 eps slot 2 deterministic
   (legM_eval_out.txt): **win 70.0% (14W/6L), picks 6.70, forms
   1.70** vs legG's 74.0 / 8.06 / 2.30 (n=50). Below legG on all
   three (picks even a hair under the band). Not weird — just worse
   on this matchup; linux_port/powerstone_v6_ppo.zip stays legG
   (md5-verified distinct from legM). Note: a first attempt died
   silently at ep 10 (9W/1L!) — it was killed by a shell timeout,
   not a crash; the full 20-ep rerun regressed to the mean.
2. **Training bring-up, PS2_NENVS=2: PAST STEP 0, AND THE P1-VIEW
   EYEBALL CAUGHT A REAL BUG (Aug 28).** First relaunch trained fine
   mechanically (22+ PPO iterations, ~40 steps/s aggregate at
   NENVS=2, timesteps continuing from legG's 27.911M, snapshot
   callback fired) — but the ep_stats CSVs read learner 62W/4L with
   dmg_out flat 2.000, opponent picking only 2.85 stones/ep. The
   opponent moved, picked, formed, even won 4 — NOT frozen — but far
   off the ~50%-by-construction expectation. Root cause (fix #7,
   selfplay_env._obs_from_view): the P1 line was PINNED onto
   _lr_synth.line, but _parse_state_once's pump-on-stale check fires
   on every opponent read (last parse is always the same frame), runs
   a frame, and tick() invalidates the pin — the opponent parsed the
   LEARNER-sorted line every step (own pos/health correct — player
   blocks are port-ordered — but stones/chests/projectiles sorted
   around its ENEMY). FIXED: parse the view's line via the pure
   _parse_line path (no pin, no pump); relaunched with
   PYTHONUNBUFFERED=1 so spawn workers' [ep] lines actually stream
   (they were block-buffered — that's why the log looked [ep]-less).
   Pre-fix CSVs archived as bridge_i*/ep_stats_v6.prefix7.csv.
   Post-fix the stats did NOT move (23W/2L) — the obs-sort fix was
   real but minor (1v1 has few stones; both sort orders nearly match).
   An A/B probe (ab_selfplay_probe.py NEW: learner vs ONE chosen
   frozen opponent) went 12-0 vs even the 31.9M checkpoint ->
   structural seat handicap, and an obs-fidelity probe (obs_probe.py
   NEW) proved the P1 VIEW FAITHFUL (positions/deltas/healths exact,
   varied policy actions on both views). Real root cause, found via
   RAM_MAP's face_norm character fingerprint (facing row carries
   character scale): **slot1 was stamped P1=AYAME (0.895) vs
   P2=Falcon (0.991) — every pool policy is a Falcon policy, so the
   opponent seat was a Falcon expert driving Ayame.** FIXED Aug 28
   without the interactive savestate maker: menu_drive.py (NEW) =
   headless menu navigation via get_frame screenshots + scripted
   button steps; drove pause -> CHANGE CHARACTER -> cycled P1 to
   FALCON -> stage select Desert Area -> re-stamped states/slot1.state
   at round start (old state kept as slot1.state.ayame_backup).
   Fingerprint now 0.991/0.991. Also fixed while in there: the P1
   view's last-action one-hot leaked the LEARNER's last action
   (now per-view, selfplay_env._view_last), and [opp] lines now log
   which pool zip each episode faces. **A/B re-probe on the new
   state: 7W/5L (58%) vs the 31.9M checkpoint — the seat is FAIR;
   bring-up BLESSED. Both sides actually fight.**
   ALSO: macOS "app crashed — restore windows?" modal can hang ANY
   headless emu boot after a prior crash (stack: NSAlert runModal) —
   cured with `defaults write org.python.python
   ApplePersistenceIgnoreState YES` (do this on any new Mac).
3. **SCALED — LEG 1 RUNNING (Aug 28 ~01:48, tmux session `ps2train`,
   caffeinate -is, log train_leg1_out.txt).** PS2_NENVS=6,
   dolphin-2..5 seeded, warm start legG. Health at launch: first 18
   eps 9W/9L (exactly the 50% self-play construction), all 9 pool
   zips sampling ([opp] lines), episodes contested (sample loss:
   dealt 1.95 bars / took 1.00). 35 min in: **92 steps/s aggregate**
   (vs ~175 hoped — GPU contention with 6 renderers; null-video is
   the known lever for a future leg, don't touch this one), 28.01M
   total steps, learner 97W/40L (71% — learning against the frozen
   pool; 500k-step snapshots will refresh it), zero tracebacks.
   4M-step leg ETA ~12h (~14:00 Aug 28). Reattach:
   `tmux attach -t ps2train` (tmux via brew, NEW on this Mac).
4. **LEG 1 COMPLETE (Aug 28, 01:48 -> 15:01, ~13.2h).** 4.00M steps
   (27.918M -> 31.918M), 84 steps/s sustained the whole way, 7,458
   self-play episodes (learner 81% by the end — climbed from the
   50/50 launch as it outgrew the frozen pool), 10 selfplay_* pool
   snapshots, 40 checkpoints_sp zips, ZERO crashes. Product:
   linux_port/powerstone_v6_ppo_selfplay_leg1.zip.
   **EVALS (Aug 28 afternoon):**
   - A/B vs legG (27.9M warm start): **7W/5L** (n=12, stochastic)
   - A/B vs ps_v6_31915459 (strongest old): **7W/5L** (n=12)
   - eval_parity slot 2, 50 eps deterministic (parity_leg1_out.txt):
     **win 98.0% (49W/1L), picks 9.76, forms 3.00** — vs legG's port
     numbers 74.0 / 8.06 / 2.30 on the identical protocol.
   Reading: modest peer-vs-peer edge (58% both probes; n=12 is
   noisy), but a LARGE jump on the COM benchmark — and leg 1 trained
   only on slot1 desert 1v1, so the slot2 FFA gain is generalization,
   not eval overfit. Self-play works on this port. Next-leg
   decisions (Blake + rig-session concurrence, Aug 28 evening):
   - **PROMOTED: leg1 IS the warm start** — powerstone_v6_ppo.zip =
     selfplay_leg1 (md5-verified); legG preserved as
     powerstone_v6_ppo_legG_backup.zip.
   - **Widen STATE_SLOTS: yes, but it needs a Blake controller
     session first.** Self-play slots must be VS-mode 2P stamps
     (both DC ports human — selfplay_env docstring); slot2 as
     stamped is a COM FFA (eval-only). Plan: make_savestates, 2-3
     more stages, TAB both ports in, BOTH PORTS FALCON (the Ayame
     lesson), stamp F3-F5 at round start, verify face_norm ~0.991
     per seat.
   - **Null-video: parked for the 7950X era** — its value case was
     M2 GPU contention; the new box renders on a 3090.
   - Before leg 2 buries it: record the reddit video via
     watch_play.py --model ./powerstone_v6_ppo_selfplay_leg1.zip
     (the 49-1 champion) while it still holds the crown.
   Note: eval boot flake bit once during the battery (the 31.9M probe
   died at init, silent); rerun succeeded — always check the output
   file has an AB RESULT line.
Known cosmetics: mutex abort at exit; "SHORT OPPONENT SET slot1" is
expected (slot1 = 1v1 self-play state); sb3 gym-wrap warning is fine.

## THE FORK (Aug 28) — plan for the next session

The port is PROVEN (gate 4 passed; rig tiebreaker confirms obs
fidelity). The project pivots from porting to scaling. Blake's list:

1. **Retire the 12700K as the training rig** — the M2 (and later a
   rented box) takes over. The rig keeps one job until then: source of
   truth for old checkpoints/notebooks not yet migrated.
2. **GitHub refresh** — audit both machines' folders for what actually
   belongs in the repo (the 12700K especially is full of scratch);
   collect the canonical set on ONE machine (the M2 copy is cleanest —
   linux_port/ + sdlarch-rl patches + docs), README rewritten BY HAND
   (Blake's voice), push from Blake's own terminal. Good first Claude
   Code task: inventory + a proposed repo manifest, human writes prose.
3. **Share it** — video via watch_play.py (NEW, linux_port/): renders
   every frame at real-time pacing while the model plays; screen-record
   it. Plus a short write-up for reddit.
4. **Compute: DECIDED (Aug 28) — buy a Ryzen 9 7950X (~$279) for
   Blake's existing AM5 board.** Rental rejected (Hetzner post-hike:
   AX102 EUR 259/mo + setup; XLC $209+/mo, small vendor; marketplace
   compute like QuickPod = stranger-hardware burst only, never the
   checkpoint home). Threadripper rejected (5975WX P620 ~$3300; 2x
   cores but only ~1.3-1.6x aggregate — per-core speed rules this
   workload). 7950X projection: ~26-28 steps/s x 14 workers = ~370-400
   steps/s aggregate, ~5x the old rig, for six weeks of rent money.
   Build notes: reputable retailer only (clearance era = counterfeit
   listings), real cooling (230W PPT), 64GB RAM comfortable, BIOS
   update first. Day one: setup script -> bench_fps.py -> let the
   measured number set N_ENVS.
5. Remaining technical threads, in order: finish the first Mac
   training bring-up (fixes #5/#6 committed, next run starts at the
   first real training step); eyeball the P1 opponent view (never
   exercised on the rig); GPU-contention test before PS2_NENVS>2;
   optional matchup re-stamp (Pete/Falcon/Pride/Julia) for the clean
   apples-to-apples eval number.

## PROJECT LAWS (permanent section — earned by 6 legs + the rig era; do not trim)

Distilled from leg 2 + the leg-3 program (Aug 29-31) on top of the rig
record. These are the load-bearing conclusions; every future leg design
should be checked against them.

1. **Gradient continuity is the engine.** A diet only teaches winning
   if wins stay reachable throughout. Self-play guarantees this by
   construction; fixed too-strong opponents guarantee the opposite.
   (Evidence: 3B/3C-SP climbed; leg2, 3A, 3D flatlined at ~0%%.)
2. **Losses carry no information about winning.** Three separate
   lv8-only diets (warm, fresh, lv8-BC-seeded) produced zero learning-
   to-win. "Train against harder opponents" is not a curriculum unless
   the model can sometimes beat them.
3. **BC priors do not transfer wins — demos must enter via DAgger.**
   A validated 23-1 human corpus, baked at 80.6%% val acc, yielded 8
   wins in 4,653 training episodes (3D). Covariate shift eats frame-
   level mimicry. Human data pays only when it relabels the POLICY's
   states (DAgger / failure-state drills), never as a seed alone.
4. **Data/priors/interface changes go ~5-for-5; reward tuning is
   0-for-5 lifetime.** (BC ceiling break, hold-until-next fix, chest
   obs restoration, self-play leg1, deep-pool discovery vs the five
   null reward legs.) Touch the data pipeline before the reward table.
5. **Opposition quality AND gradient budget must both be right.**
   3C had the best opponents (3B's lineage via the shared pool —
   accidental league training, the program's discovery) but only 2/6
   workers on them, and transferred worst. Don't split the budget with
   a dead stream.
6. **Promote the best checkpoint, never the last.** PPO churn:
   leg2's final zip evaled 4.0%% while its mid-leg checkpoints held
   8-16%%. Sweep before promoting; entropy stability does not protect
   the final snapshot.
7. **The lv8 wall stands.** No 2M-step fresh lineage has scored one
   deterministic lv8 win (0-for-200 eval episodes across 4 legs). Only
   the 31.9M lineage wins there (15%%). Respect what lifetime buys.
8. **Ops:** worker boot stagger 20s (Metal init race killed 3 launches
   at 6s, plus 2 chained launches — add retry-on-EOFError to
   launchers); leg launches via launcher SCRIPTS, never nested-quoted
   tmux; menu navigation is fully headless via menu_drive.py; one
   savestate slot number = one meaning per machine, document re-stamps.

## Findings worth remembering (the short version of Aug 24-28)

- The lua-era env assumes a free-running emulator; in-process libretro
  advances only when pumped. Every hang traced to that one assumption
  (liveness check, reset polls, loadstate, episode determinism).
- "Quiet degrades" aren't: the unported chest scan read as a 60-point
  win% collapse, because the policy TRUSTED those dims. If the model
  was trained with an input, ship the input.
- Deterministic frozen evals read far above training-time bands
  (92% vs 63-75 on the rig itself). Compare like protocols only.
- Behavioral metrics (picks/forms) are the real cross-machine parity
  test; win% also absorbs matchup and COM variance.
- Two AI sessions + one human across two machines works IF one file
  (this one) stays the single source of truth and each folder has one
  driver.

Continuation doc for the Claude session that ported the rig's RL setup to
the M2. Read alongside README_MIGRATION.md / MAC_TEST.md / README_PORT.md
(kit 1) and README_MIGRATION2.md (kit 2, in ~/Downloads/macbook_migration2).
HOWTO_LINUX_SERVER.md + setup_linux.sh (this folder) are the rented-server
recipe, current as of the state below.

## Scoreboard

- Gate 1 (RAM): **PASSED.** SYSTEM_RAM 16 MiB, HEALTH OK at delta +0x0
  (no RAM_DELTA needed), v7 synth line = 80/80 fields. Probed from
  states/slot1.state.
- Gate 2 (savestates): **PASSED.** slot1 = HvH 1v1 desert (good).
  slot2 re-stamped Aug 24 evening: desert, COM lv3, true FFA, bot on
  P2 — verified live with diag_state.py (4x1000.0 healths at frame
  ~306 hands-off, COMs actively fighting).
- Gate 3 (buttons): **PASSED.** calibrate_buttons table clean: dpad
  sign-consistent (diagonal axes = camera rotation, fine), attacks lunge,
  trigger rows alias face buttons (the GAME's combo shortcuts, not a
  mapping bug). DC_TO_RETRO unchanged. Xbox pad dpad-as-buttons (11-14)
  fixed in make_savestates.py.
- Gate 4 smoke: **PASSED** (Aug 24 evening) — "smoke OK — 100 steps"
  after env fix #1 below. bridge alive, line=v7, obs_dim=122.
- Gate 4 parity: **PASSED — Aug 28, after the kit-#3 chest-scan port.**
  50 eps deterministic, slot 2 (parity_chest_out.txt):
  **win 74.0% (37W/13L) IN BAND [63-75]; picks 8.06 ABOVE band
  [6.8-7.5]; forms 2.30 ABOVE band [1.4-1.9]** — above = ok, frozen
  deterministic reads high. "PARITY PASS — obs semantics survived the
  port." (The Aug-24 14% fail is preserved below for the record; root
  cause was the unported object-ledger scan: dark chest dims + pad
  chests fed to the model as stones.)
  **Rig tiebreaker landed (Aug 28, eval_abc, same protocol): win 92.0%,
  picks 7.08, forms 2.28.** Reading: picks/forms match the Mac (8.06 /
  2.30) almost exactly -> obs port CONFIRMED faithful. Deterministic
  reads far above the training band (92 vs 63-75). The 18-pt win% gap
  (92 rig vs 74 Mac) with matched behavior points at MATCHUP, not code:
  rig lineup = Pete/FALCON/Pride/Julia; **Mac lineup CONFIRMED by
  Blake (Aug 28): opponents Ayame/Pete/Accel — a different team**,
  which also explains the Mac COMs hoovering ~2x the stones (13-15 vs
  ~7/ep; Ayame). Matchup hypothesis CONFIRMED; case closed. Optional
  homework only: re-stamp to the exact rig lineup for a clean
  apples-to-apples number. Self-play training does not depend on the
  COM matchup.
- Training: **ONE pip install FROM RUNNING** (Aug 28 late). The
  PS2_NENVS=2 bring-up burned down every seam in order:
  1. shimmy missing -> `pip install 'shimmy>=2.0'` DONE (sb3 wraps the
     old-gym env via its compat layer; works).
  2. system/dolphin-1 seeded from dolphin-0 DONE.
  3. macOS fork corruption + concurrent Metal pipeline race killed
     workers -> FIXED in train_selfplay.py: SubprocVecEnv
     start_method="spawn" + 6s-per-instance init stagger. Verified:
     both workers boot clean, both bridges alive, warm start loads.
  4. tensorboard missing -> `pip install tensorboard` DONE.
  5. First real training step: ps2_ram's lazy-compose refactor had made
     `line` a read-only property, but selfplay_env's view-swap ASSIGNS
     it -> FIXED: line has a setter again (pins the value for the
     current frame; next tick invalidates).
  6. selfplay_env._obs_from_view was still a sketch (its own NOTE):
     called nonexistent `_build_obs` -> WIRED to the parent's
     `_observe(s, prev)` with per-view prev tracking (velocity deltas)
     AND an _active_opp flip — without it the P1 view lists ITSELF as
     its opponent. EYEBALL THE FIRST EPISODES: the P1 view is the one
     thing the Windows rig never exercised (e.g. if the opponent stands
     still or acts degenerate, suspect this block first).
  Command: SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.
  PS2_CORE=<flycast dylib> PS2_NENVS=2 python -u train_selfplay.py
  Then: check per-process GPU% in Activity Monitor with 2 workers
  before raising PS2_NENVS; run long legs under tmux; STATE_SLOTS=[1]
  is deliberate (one stage until stable — widen later). Note the
  "SHORT OPPONENT SET slot1 1/3" lines are expected: slot1 is the
  1v1 self-play state.

## CURRENT BLOCKER: parity FAIL — legG far below the slot-2 band

50-ep frozen deterministic eval, slot 2, Aug 24 evening (parity_out.txt):
win 14.0% (7W/43L) vs band 63-75; picks 4.60 vs 6.8-7.5; forms 0.46
vs 1.4-1.9. Every mechanical layer works: buttons (dmg dealt 4-6 bars/ep),
forms when reached (dmgF > 0, the sole 2-form episodes include the wins).
The deficit is concentrated in GEM ACQUISITION.

**RESOLVED Aug 28 — kit #3 arrived (~/Downloads/kit3: powerstone.lua,
RAM_MAP.md, KIT3_NOTES, RIG_BENCH_ANSWER) and the chest scan is PORTED.**
ps2_ram.py now runs STONE_OBJ_MODE (lua stoneObjScan 1:1): object arena
at 0x8C4FBD30, 110 x 0x430 slots, hdr low byte 0x09, vt classify —
loose stones 0x0C0CBCB0 ARE the line's stones now (doctrine flip: pads
hold chests; the old spin-gate sweep was feeding pad-chests to the model
AS stones — the gap was double, not just dark chest dims). Chest
fragment live: chestN, fallN, 2 nearest resting chests. Also: full lua
PROJ_EXCLUDE list + band excludes ported, and the line now composes
LAZILY (kills the +32% synth tax from the bench). Verified offline
against the env's own parser with a synthetic RAM image; legacy-mode
regression-tested. Legacy fallback: ps2_addr.STONE_OBJ_MODE = False.
Rig-side numbers (RIG_BENCH_ANSWER): rig = 7.9 steps/s/instance, ~79
aggregate; M2 = 3.7x per instance, 2.2x rig aggregate. Rig deterministic
legG eval RUNNING (Aug 28; early: 2/2 wins, tracking band — confirms
the low Mac read was the port gap). **Rig slot2 lineup recovered
(Blake, eyeballed at eval launch): P1 Pete, P2 FALCON (the bot — RAM_MAP:
bot is ALWAYS port 2 = Falcon; legG is a Falcon policy), P3 Pride,
P4 Julia, desert, COM lv3.** The Mac slot2 re-stamp must match — P2
not-Falcon alone would depress every number. Verify/re-stamp before
the parity re-run.
NEXT: confirm lineup (re-stamp if needed) → smoke → 50-ep parity —
that is the gate-4 verdict.

**The original finding (kept for the record) — chest obs were hardcoded
zero.** ps2_ram.py's TODO:
STONE_OBJ_MODE (the Aug-10 object-ledger scan) was never ported; the v7
chest fragment is zeros, so obs [107..110] always read 0. legG trained
WITH live chest obs, and chests are the gem source (Sec 15: pads hold
chests, not stones). Signature matches exactly: COMs pick 10-25
stones/ep, bot 4.6; bot rarely holds 3 gems -> no forms -> loses 3v1
wars of attrition. NOT fixable from the kits: ps2_addr.py has no chest
addresses, and powerstone.lua / RAM_MAP.md are only on the rig.
**KIT #3 REQUEST: powerstone.lua + RAM_MAP.md** (minimum: chest class
window, object-ledger base/stride, chestN/fall field offsets) — then
port the scan into StateLineSynth._sweep_pool/_compose.

**Cadence: TESTED AND RULED OUT** (Aug 24 late). 20-ep eval with
PS2_FRAME_SLIP=2 (slip2_out.txt): win 5.0%, picks 4.45, forms 0.35 —
statistically identical to the slip-0 baseline (14%/4.60/0.46, n=50).
Extra held-input frames per step move nothing; the deficit is in what
the model SEES, not when it acts. The knob stays in the env for
future experiments.

**Eval mode: ALSO RULED OUT** (Aug 25). 50-ep STOCHASTIC eval
(--stochastic, added by the rig-side session; stoch_out.txt): win
10.0% (5W/45L), picks 4.88, forms 0.52, distinct-episodes~50. Same
regime as deterministic — sampling vs argmax changes nothing, and with
the widened 0-599 loadstate stagger every episode is distinct. The
port gap is CONFIRMED and observational. Chest obs zeros = prime and
now effectively sole primary suspect; kit #3 is the critical path.
(Division of labor agreed Aug 25: the Mac session drives linux_port/;
the rig session owns the rig and is packaging kit #3 — powerstone.lua
+ RAM_MAP chest section — plus the rig slot2 character lineup and a
rig-side deterministic 50-ep legG eval as band calibration.)

**Remaining secondary: legacy stone sweep** (spin gate) vs the
object-ledger scan — stone picks do work, just fewer, so a possible
contributor, but the chest gap is the dominant suspect.

## Libretro env fixes shipped Aug 24 (all in powerstone_env_libretro.py)

The lua-era parent assumes a BACKGROUND emulator advancing in wall time;
in-process libretro frames advance only when pumped. If the parent env is
ever refreshed from the rig, these overrides must survive:

1. `_wait_for_bridge` override — pumps run_frames(4) between its two
   reads (was: sleep 0.3s, frame never moved, "Bridge frame counter not
   advancing" x4 -> the old smoke blocker. The old HANDOFF prime suspect
   — state-file path — was WRONG; _read_state does reach the subclass
   _parse_state_once).
2. Pump-on-stale in `_parse_state_once` — re-reading the same synth
   frame runs 1 frame first, so reset()'s match-ready poll and
   _wait_frames make progress instead of spinning (the eval hang).
3. loadstate intro pump in `_send` — after any loadstate, pump up to
   1200 frames until match-ready(provisional): round-start stamps play
   out their ~306-frame intro instead of starving reset's retry loop
   (which reloads every 3rd try, wiping progress).
4. Random 0-59 frame post-load stagger — without wall-clock jitter a
   deterministic policy replays BYTE-IDENTICAL episodes (observed).
5. `PS2_FRAME_SLIP` knob — see cadence suspect above. Default 0.

Plus: train_selfplay.py warm start now passes custom_objects
(clip_range 0.2, lr 2.5e-4) — the rig's pickled lambdas don't
deserialize under py3.11; predict() never cared, .learn() would crash.
diag_state.py (NEW) = headless savestate triage (health/sec + verdict).

## Known crashes (non-blocking, documented)

- **Boot flake:** intermittent `mutex lock failed` abort or segfault
  during emu init, disproportionately the FIRST boot after
  login/reboot. Retry has always worked. Threaded rendering is already
  forced off (helped, didn't fully cure). If it ever fails twice in a
  row, debug properly (lldb / SDLARCH_LOG=1).
- **Exit abort:** `mutex lock failed` AFTER all results print, at
  process teardown. Cosmetic for gates; emu.close() added everywhere but
  didn't cure. Revisit before long SubprocVecEnv training if workers die
  dirty.

## Inventory (what lives where)

macbook_migration/ (this folder):
- `sdlarch-rl/` — harness, PATCHED (do not re-clone; patch list in
  HOWTO_LINUX_SERVER.md "Patches" section). `_retro.so` builds to repo
  root; rebuild = `cmake --build sdlarch-rl/build`.
- `linux_port/` — all scripts, patched (HLE BIOS + VMU + threading-off
  variables set in every entry point; pad/dpad + display flip in
  make_savestates; --state option in probe_ram; "player" cmd in bridge;
  synth priming + /dev/shm fallback in powerstone_env_libretro;
  eval_parity.py NEW — 50-ep frozen eval with the band baked in).
- `linux_port/states/` — slot1 (good), slot2 (needs re-stamp, see above).
- `linux_port/system/dolphin-0/` — VMUs + flash from the rig, in BOTH
  root and dc/ + dc/data/ (flycast reads dc/; completed save with
  unlocks CONFIRMED working — Pride + desert present, VMUs visible).
- `linux_port/opponent_pool/` — 8 ps_v6 checkpoints (0.2M→31.9M).
- `linux_port/powerstone_v6_ppo.zip` — Leg G warm start (copy of
  powerstone_v6_ppo_legG_27911k.zip).
- `linux_port/powerstone_env_v6.py` — from kit 2; no local imports;
  needs `gym` (0.26.2 now in venv).

## Bench (Aug 25, M2 Pro, bench_fps.py — NEW, in linux_port/)

A raw core 324.8 fps (5.4x RT) | B +synth 245.9 fps (+32% synth cost)
| C full env.step 29.3 steps/s = 250.9 fps incl. resets, 8.6 frames/step,
~0.7 min/ep. Env python layer ~free (B~=C fps); loop is emulation-bound.
GPU rendering ON during all of this (Apple GL4.1, ~39% GPU). Post-parity
speed levers, in order: lazy-compose in StateLineSynth (line is built
EVERY frame but read once per 8.6 — do it with the chest port, same
file), null-video for training runs, threaded_rendering re-test.
Training math: 6 workers ~175 steps/s -> 4M-step leg ~6.5h on the Mac.
Run the same bench on the rig + the rented box before sizing anything.

## Windows band, slot 2 (desert lv3 true-FFA) — gate-4 target

**win% 63–75, picks/ep 6.8–7.5, forms/ep ~1.6** (training-time band;
frozen deterministic reads a few points HIGH — above band = pass, below
= suspect the port). Borderline tiebreaker: rig can run a fresh 50-ep
frozen eval of the same zip on request. Already encoded in eval_parity.py.

## Environment / commands cheat-sheet

Every new terminal: `source ~/ps2rl/bin/activate` then
`cd ~/Documents/macbook_migration/linux_port`.
Every command prefix: `SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.`
Core: `~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib`
(installed via buildbot curl, Aug 22-23 nightly). Game: `../Power Stone 2
(USA).chd`. Debug core logs: prepend `SDLARCH_LOG=1`.

- savestate maker (visible window, kb + xbox pad, F1-F7 stamp, TAB port):
  `python make_savestates.py --core <core> --game <game> --states ./states`
- gate 1: `python probe_ram.py --core <core> --game <game> --state states/slot1.state`
- gate 3: `python calibrate_buttons.py --core <core> --game <game> --state states/slot1.state`
- gate 4 smoke: `PS2_CORE=<core> python powerstone_env_libretro.py`
- gate 4 parity: `python eval_parity.py --core <core> --game <game> --slot 2 --episodes 50`
- train: `PS2_NENVS=6 python train_selfplay.py` (after parity passes;
  multi-instance needs system/dolphin-N seeded per instance — setup_linux.sh
  shows the loop; also expect the sb3-2.9-vs-old-gym-API wrapper question
  at SubprocVecEnv time: env is old-gym 4-tuple style, sb3 2.9 wants
  gymnasium — may need `pip install shimmy` or a thin wrapper. UNTESTED.)

## Next actions, in order

1. ~~Cadence discriminator~~ DONE — ruled out (see above).
2. KIT #3 from the rig: powerstone.lua + RAM_MAP.md (chest section at
   minimum). Port the object-ledger chest scan into ps2_ram.py
   (StateLineSynth._sweep_pool + _compose chest fragment), re-run
   eval_parity 50-ep.
3. Optional band cross-check while bridges are busy: rig runs its own
   fresh 50-ep frozen eval of legG_27911k on slot 2 (deterministic
   reads a few points high — calibrates the band for frozen evals).
4. Parity passes → train_selfplay (sb3-2.9 vs old-gym API at
   SubprocVecEnv time still UNTESTED — may need shimmy or a wrapper).
5. HOWTO_LINUX_SERVER.md is synced with all of the above (Aug 24).
