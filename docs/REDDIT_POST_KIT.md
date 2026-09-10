# REDDIT POST KIT — verified numbers + outline
*(assembled Sep 1, 2026, from HANDOFF.md and eval outputs; prose is yours to write.
Every number below traces to an eval output file or training log on the M2.)*

---

## Title options

- I taught an RL agent to play Power Stone 2 (Dreamcast) from RAM values — no pixels. Here's what 6 controlled training experiments taught me.
- My brother-in-law (ML engineer) gave me one piece of advice about my Dreamcast RL bot. Testing it properly took 6 experiments and broke half my assumptions.
- RL on a 26-year-old Dreamcast game: my fresh 6M-step agent just caught the 32M-step champion. The recipe surprised me.
- What actually worked (and didn't) training a fighting-game RL agent: BC, hard opponents, self-play, and a league — a controlled comparison.

## TL;DR block (numbers verified)

- Game: Power Stone 2 (Dreamcast), 4-player arena fighter, via Flycast/libretro headless
- Observations: 122 dims read straight from emulator RAM — zero pixels
- Actions: 10 discrete, one decision every ~8.6 frames
- Hardware: started on a 12700K Windows rig, ported to an M2 Pro MacBook (3.7x faster per instance); 7950X incoming (~5x aggregate vs M2)
- Total lifetime across all models: ~2,000 in-game hours (Pokemon Red RL used ~50,000 for the first gym — we're at 4% of that scale)
- Headline: a fresh lineage went from "cannot win a single game" to DEAD EVEN (6-6) with the 31.9M-step champion in 6M steps / ~2 days of laptop time

---

## STORY ARC (suggested sections, with the numbers that go in each)

### 1. The setup (short)
- Emulator RL, RAM-based obs (found by memory scanning), self-built libretro harness
- The old lineage: 31.9M steps over a month, stalled at COM level 5, never reached 6
- Rig-era scar tissue worth one line each: reward tuning went **0-for-5** lifetime;
  data/prior/interface changes went ~5-for-5

### 2. The inciting incident
- BIL (ML engineer who works on game bots professionally) over a family
  conversation: "too much data from weak battles — just train against max difficulty"
- Also relearned my own project's forgotten conclusion, written weeks earlier in
  the lab notebook: "lv5 needs a PRIOR... human demos > aimbot farm > more reward work"

### 3. Experiment 0 — the naive version fails (leg 2)
Warm-start the 31.9M champion, feed it only max-difficulty (lv8) battles, 4M steps:
- Training win% flat ~10% the whole leg
- Final model scored WORSE everywhere: lv8 eval 4.0% (baseline 15.0), lv3 benchmark
  88.0 (was 98.0), lost 3-9 to its own parent
- Checkpoint sweep (n=50 x 4 checkpoints): win% bounced 8-16% — churn, no peak
- Lesson #1: exposure to losses carries no information about winning
- Lesson #2 (from the sweep): promote the best checkpoint, never the last one

### 4. The controlled program — 4 legs, one seed, one variable each
All from the same fresh BC seed (256x256 net, behavior-cloned from 258k
demo pairs), 2M steps each, identical eval battery (n=50 deterministic):

| leg | diet | lv8 eval | lv3 eval | vs own seed | vs champion |
|-----|------|----------|----------|-------------|-------------|
| A | lv8 battles only | 0.0% | 14.0% | 10-2 | 0-12 |
| B | self-play vs itself | 0.0% | **40.0%** | **12-0** | **4-8** |
| C | mix (4 lv8 + 2 self-play workers) | 0.0% | 14.0% | 11-1 | 2-10 |
| D | lv8 battles, seeded with MY 23-1-vs-lv8 play | 0.0% | 28.0% | 7-5 | 1-11 |

The narrative beats inside the table:
- **Leg A:** 0 wins in its first 856 episodes... and its last 856. Dense shaping
  moved (picks doubled) but you cannot gradient-ascend to victories you never sample.
- **Leg B:** the only leg that learned to WIN anything. 4-8 vs the champion
  (16x its raw lifetime; ~4-5x its EFFECTIVE lifetime per the plateau analysis
  — use the effective number when arguing, the raw number when marveling).
- **Leg C's accident:** its self-play workers unknowingly fought leg B's snapshots
  (shared pool dir) — accidental league training. Best climb of the program
  (14.7% -> 54.3% mid-leg) but only 2/6 workers got it; transferred worst.
  Lesson: opposition quality AND gradient budget must both be right.
- **Leg D, the heartbreaker:** I recorded 24 rounds vs three lv8 COMs on the rig,
  went 23-1 (96%), baked an 11,704-pair corpus into the seed at 80.6% val accuracy.
  Result: 8 wins in 4,653 training episodes. My play did NOT transfer.
  Textbook covariate shift — the clone drifts off my state manifold in seconds
  and I never demonstrated recovering, because I wasn't losing.
  (This is the DAgger sales pitch, lived.)

### 5. The synthesis — and the payoff curve
Take leg B's recipe (full self-play budget) + leg C's discovery (deep league pool:
every old checkpoint 0.2M-31.9M + every program model), compound one lineage:

| leg | lineage lifetime | lv3 benchmark | vs its parent | vs the 31.9M champion |
|-----|------------------|---------------|---------------|----------------------|
| B | 2M | 40.0 | 12-0 (vs seed) | 4-8 |
| 4 | 4M | 42.0 | 8-1-3 | 1-11 |
| 5 | 6M | **50.0** | **11-1** | **6-6 — DEAD EVEN** |
| 6 | 8M | *(running tonight)* | | |

- **HONESTY CAVEAT (Sep 2 audit — include this in the post; it's the
  credible move):** the head-to-head "6-6"/"7-5 vs the champion" probes ran
  on the SAME 1v1 state the lineage trained on, against a pool that a sort
  bug had skewed to ~60%% leg1-snapshots — so those numbers partly measure
  "practiced against the test." They're also n=12 (95%% CI on 6/12 ~ 25-75).
  The clean, held-out claim is the lv3 FFA benchmark at n=50: different
  stage, different opponents, never trained on. Lead with THAT curve.
  (A bug-fixed league + a 50-ep A/B are re-running; update numbers before
  posting. Reviewers WILL find this if you don't say it first — and the
  bug-hunt story is itself good content.)
- Each leg decisively beats its parent; the benchmark compounds 40 -> 42 -> 50
- Leg 5's training curve vs the league: 38% -> 28% (its parent's snapshots joined
  the pool mid-leg) -> 47% -> 52%. The pool fights back; the agent adapts.
- Effective-steps point (good for discussion): the champion's 31.9M steps include
  a long plateau era — its real learning was maybe 15-20M. The fresh line spends
  every step post-lessons. That's why 6M catches 31.9M.

### 6. What still stands: the lv8 wall
- No fresh model has won a single lv8 eval game: 0-for-300 episodes across 6 legs
- Only the 31.9M champion wins there (15%) — lifetime buys what nothing else has
- Honest cliffhanger + sequel hook: the 7950X (5x throughput) arrives soon;
  100-200M steps inside a week; somewhere in that regime the wall stops being a wall

### 7. Closer options (your call)
- The parenting angle: 5 years of watching RL happen in real time at home;
  every law the experiments proved maps onto raising kids (too-harsh penalties
  breed corner-campers; challenges need to be winnable; watching a demo isn't
  skill; the best environment grows with the learner)
- The BIL callback: his advice was half right in the best way — the diagnosis
  (data distribution) survived everything; the remedy took six experiments to find
- "This is so much more fun than doomscrolling" — night-one energy, still true

---

## APPENDIX — verified reference numbers

**Baselines (n=50 deterministic unless noted):**
- Champion (leg1, 31.9M steps, self-play): lv8 15.0% / lv3 98.0% (9.76 picks, 3.00 forms/ep)
- My own play vs three lv8 COMs: 23-1 (96%), 24 rounds, 11,704 recorded pairs
- BC seed val accuracy: 80.6% overall (weak spots: jump 49.9%, grab 27.5%)

**Leg 2 (warm+lv8, 4M steps):** train flat ~10%; final lv8 4.0 / lv3 88.0 / 3-9 vs parent; sweep 8.0/16.0/10.0/12.0 across checkpoints

**Program legs (2M each, common seed):** table above; leg A quarters 0.0/0.0/0.3/0.2%;
leg D quarters 0.00/0.26/0.09/0.34%; leg C self-play stream 14.7/19.0/37.1/54.3%;
leg B vs its own pool 88.0/92.6/93.9/95.8% (soft mirror — caveat it)

**League legs:** leg 4 quarters 29.8/29.5/20.0/22.8 (len 490->943);
leg 5 quarters 38.3/28.0/47.2/52.1; batteries in the table above

**Scale math:** 1 step = 8.6 frames @60fps; 2M-step leg = ~80 in-game hours ≈ 7h
wall on M2 (6 emulator workers, ~80 steps/s); champion lifetime ≈ 1,270 in-game hours;
everything ever ≈ 2,000 hours

**Ops war stories (great for comments):** the chest-obs port bug (obs dims zeroed ->
win rate collapsed 74% -> 14%, fixed = instant recovery — "if the model trained with
an input, ship the input"); the Ayame seat bug (every pool policy is a Falcon expert,
one savestate had the wrong character — found via a character-scale RAM fingerprint);
the macOS Metal boot race (staggered worker launches + watchdog relaunchers)

---

## ASSETS TO MAKE (before posting)

1. **THE VIDEO** — watch_play.py rendering leg1 (or leg 5/6 if it takes the crown)
   in real time; screen-record 2-3 matches incl. a transform. Still unrecorded.
2. **The compounding chart** — lv3 benchmark across legs (14/40/42/50/...) with the
   champion's 98 as a reference line; make_readme_charts.py on the rig repo is the
   tooling precedent
3. The four-way program table as an image (reddit tables render poorly on mobile)
4. Optional: a clip of leg A flailing vs leg 5 fighting — before/after is visceral

## WHERE TO POST
1. r/reinforcementlearning — full writeup, lead with the table + video
2. r/MachineLearning [P] — same content, tighter abstract up top
3. After those land: r/emulation (engineering angle), r/Fighters + r/dreamcast
   (video-first, light writeup), optionally r/programming (debugging saga framing)
Check each sub's current rules before posting.
