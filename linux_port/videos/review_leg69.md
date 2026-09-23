# Scouting report — league leg 69 (Desert Area)

**1. LOSS (ep01, round 1 of 3, 0:00–0:51)**
Bot skates solo off the cactus rise straight at Pride (contact ~0:02, before ACTION! at 0:04) — fast engage again. All 3 opponents converge into a chest scrum by 0:08-0:11. Stones mismanaged: picked=2/lost=3, forms=0/1 — bot never transforms; the ~0:41-48 green-winged missile/plane swarm is tagged ENEMY (green = Accel) and 2P shows no transformed model, so that's Accel's own special, not bot's. No KO either side until the very end. In the last-12s strip the bot is grabbed/launched airborne into that swarm's chaos (~rel 9.75s), then Ryoma's blade connects on it mid-air at rel 11.0s (~0:50) — 2P is the only portrait X'd, ending the round. Purely reactive: no evasion read, bot never breaks off while being juggled.

**2. WIN (ep03, round 3 of 3, 2:45–4:22)**
Unlike the loss (and unlike leg66-68's fast opens), bot opens solo and drifts toward the 3-enemy cluster instead of rushing it — first contact not until ~14s in. Stones dominate: picked=9/lost=1, forms=3/4, dmg +6.00/-0.58. Ryoma (3P) falls first, ~rel 4.5s into the tail, juggled by a stage lightning/rockfall hazard — not a fighter's own move. With ~10s left, bot's 3rd transform of the round shows a visibly golden/winged 2P model that fires a missile/plane swarm at rel 10.0-10.25s — Falcon's own fusion special per rubric. Accel (4P) dies inside it at rel 10.75s; Pride (1P), last survivor, is swept up by the same drifting swarm and dies at rel 11.0-11.75s, sealing the win — both late kills are bot's own credit.

**3. PATTERNS**
- The fast-open pattern (leg66-68) breaks in this win round: bot opens away from the cluster instead of rushing in — watch if this recurs.
- Loss again lands forms=0/1 vs win's forms=3/4 — the stone-retention gap flagged in leg68 persists across a second leg.
- No bomb-prop-adjacent kill this leg (a leg67/68 pattern) — the losing and winning kills instead come from a stage hazard and bot's own swarm.
- Bot's ~14s solo drift before engaging in the win round could read as deliberate spacing; at 1fps this isn't distinguishable from just slower pathing — no clear anticipation signal visible, call it none confirmed.

**4. SUGGESTION / TO VERIFY**
Vs leg68: the recurring "unexplained death" (isolated bot, no attacker shown) does NOT repeat here — this loss has a clear, visible attacker (Ryoma's mid-air slash), unlike leg67/68's pattern.
Suggestion: forms=0/1 (or 0/3) has now shown up in every reviewed loss round (leg68, leg69) — check whether transform-closing is systematically weaker in losing rounds specifically, not just variance.
Verify: episodes.txt's win-round stats line for leg69 is identical to leg68's except chests=23 vs 20 — confirm this isn't a stale/duplicated line in the logging pipeline before trusting it.
