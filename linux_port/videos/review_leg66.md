# Scouting report — league leg 66 (Desert Area)

**1. LOSS (ep01, round 1 of 3 losses, 0:00–1:47)**
Intro shows the bot alone by a large cactus on a rocky rise (0:00, ACTION! 0:04); it closes into the 3-opponent cluster fast (~3-4s, by 0:07), continuing leg65's fast-close pattern rather than leg64's slow one. Scrum runs across open sand/cacti with chests (stones picked=5/lost=3); a robot/plane swarm appears ~0:26 near a gold-glowing "2P" (likely the bot's own fusion special, forms=1/3) and again ~1:40-41. Ryoma (3P) is the only confirmed KO, ~1:22 (HUD X), after which HELP tags recur on the bot 1:22-1:39 while boxed in by Pride/Accel. Unusually, the last-12s+tail strip (through 1:47) never shows the bot's (2P) bar crossed out — Pride, bot, and Accel are all still alive at the final sampled frame — so this round looks like it ends by timeout/placement rather than a visible bot elimination; "how it dies" is not confirmable this leg.

**2. WIN (ep04, round 4, 4:42–6:39)**
Same fast opening (ACTION! 4:36, contact ~4:40). A long scrum across sand/rock/water nets stones picked=5/lost=0, opp stones down 13 (forms=2/3) — the bot visibly transforms into its glowing gold form ~5:06-13, throwing a missile/robot swarm tagged "2P" at ~5:12. Ryoma (3P) is already down entering the last-12s strip (~6:25, KO itself not visible). Pride (1P) falls next, ~6:33-34, in a white explosive burst near "2P" (plausible but not certain bot credit). Accel (4P) is last, ~6:36-38, inside a second robot/plane swarm tagged "2P" — the rubric's fusion-special signature — credited to the bot, leaving it the sole survivor.

**3. PATTERNS**
- Fast round-opening closes (~3-4s) continue in both rounds, matching leg65's reversion away from leg64's slow close.
- HELP tags recur on the bot even while it's ahead (win ep04, 6:20-31) — same "ganged while winning" pattern as leg64/65.
- Loss ep01's end is a new failure mode: no visible bot-death X anywhere in the tail strip, unlike leg65's visible red KO-flash — the round may be lost on timeout/placement, not a death.
- Win ep04 lands 2 of 3 KOs (Accel certain, Pride probable) adjacent to the bot's own robot-swarm transform — third leg running (64/65/66) with swarm-adjacent finishes.

**4. SUGGESTION / TO VERIFY**
Compared to leg65: closing speed and "ganged while winning" repeat unchanged, but leg66's loss breaks the "off-camera bot death" streak — this time showing no bot elimination at all in the captured window, suggesting some losses are timeout/placement, not deaths.
Suggestion: since swarm-adjacent kills recur every leg (64-66), check whether the fusion is auto-triggering near clustered opponents vs. being held for a deliberate finish.
Verify: pull the per-tick alive/placement log for loss ep01 1:40-1:52 to confirm whether the bot actually dies or the round times out with it still alive — this changes whether "how it dies" even applies to this round.
