# Scouting report — league leg 68 (Desert Area)

**1. LOSS (ep01, round 1 of 5, 0:00–~1:17)**
Bot opens solo on the cactus rise (ACTION! 0:04), closes fast into the 3-opponent cluster (contact ~0:07) — same quick-close as leg66/67. Chest-heavy scrum through 0:10–0:35, but stones are mismanaged: picked=2/lost=3, forms=0/3 — bot never reaches a transform, while opponents combine for 3 (ice/beam bursts ~0:18, 0:22, 0:41-53 tag Ryoma/Accel, not bot swarms, per rubric). No confirmed kill either side through 1:04. In the last-12s strip the bot stands alone by a chest, away from the 3-enemy huddle, at 1:05 (65s) with no visible hit on it; its 2P bar is already X'd by 1:11 (71s) with no attacker shown on screen.

**2. WIN (ep05, round 5, ~7:10–9:06 / 430-546s)**
Fast open again (ACTION! 7:10, contact ~7:12). Bot dominates stones (picked=10/lost=3, forms=3/1) and damage (+6.00/-0.64). Pride (1P) is first out, ~8:02-03, apparently caught inside Ryoma's (3P) own ice/beam transform — opponent-on-opponent, not bot credit. Accel (4P) falls next, ~8:50-51, amid a red/white burst coinciding with an on-map bomb-prop countdown ("8"→"3" ticking 8:53-59) rather than a visible bot swarm — likely bomb credit, echoing leg67's bomb-assisted kill. Ryoma (3P), last survivor, goes down ~9:03-05 inside a large robot/plane swarm with the bot the only character left alive on screen — Falcon's own fusion special per rubric, clear bot credit for the finishing KO.

**3. PATTERNS**
- Fast opens (~2-7s to contact) now hold across three straight legs (66, 67, 68).
- Loss round's forms=0/3 is a new low: 14 chests opened but only 2 stones kept, no transform, vs. the same match-day's win round at forms=3/1 — looks like a stone-retention problem, not just bad luck.
- A bomb-prop-adjacent kill recurs for a second straight leg (leg67 loss ~1:56; leg68 win ~8:50), now a pattern rather than a one-off.
- HELP tags cluster right before the win round's late kills (8:53-9:05), matching the recurring "ganged" callout from prior legs.

**4. SUGGESTION / TO VERIFY**
Vs leg67: the fast open repeats, and the loss round again ends in a late, cause-unclear X (bot isolated near a chest, dead one frame later, no attacker visible) — the same "unexplained death" leg67 flagged, now twice in a row. First leg reviewed with 4-frame stacking: no anticipation or hesitation reads through at 1/4fps — the isolated bot still looks reactive, drifting off alone rather than tracking the fight, not evading a read threat.
Suggestion: check whether forms=0/3 losses correlate with chest-opening crowding out stone pickup (14 chests vs. 2 stones kept).
Verify: pull the frame-level attacker/damage log for loss ep01 1:05-11 (65-71s) to identify what killed the bot off-screen.
