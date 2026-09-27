# Scouting report — league leg 89 (Desert Area)

**1. LOSS (loss_ep02, round 2, 78-163s).** forms=1/2, picked=9 lost=7, dmg +4.66/-1.00. Bot grabs stones hard early (9 picked, more than the win's 5) but bleeds most back in a 4-way stone scrum. Its one transform (missile/plane swarm, ~abs161s) coincides with 4P Accel's X on the same frame — likely bot (swarm). Bot dies ~1s later (abs~162s) with 1P Pride and 3P Ryoma both adjacent in the same chaos — uncertain single attacker, per rubric.

**2. Does it back off from an opponent's transform?** Partly. 3P Ryoma's own transform (stone-gauge flash under 3P's portrait, sheet013 t2:29) crashes 4P Accel's health to a sliver by t2:32 while 2P's own bar stays ~90% full the whole time nearby — bot is not caught in that blast, unlike Accel. But it does not back off from the later chaos that kills it.

**3. Cautious when low on health?** No. In the last12s strip, 2P's bar is down to a bare yellow sliver from t9.75-10.5 (~abs159.75-160.5s) yet it stays parked in the scrum beside Pride rather than disengaging, and goes down about a second later.

**4. Keeps stones after being hit?** Mixed. Sheet013 shows 2P holding 1 stone icon steadily t2:30-2:32 right next to Ryoma's transform blast without losing it. But lost=7/9 overall is very high; the individual loss frames aren't resolvable at 1fps/4fps — spread across the round's frequent sword-clash contacts (sheets008-012).

**5. WIN (win_ep01, round 1, 0-78s).** forms=2/0, 6% health lost, 0 stones lost (picked=5). First transform (~abs65-66s) double-KOs 3P+4P together (likely bot, swarm); second transform (~abs76-77s) finishes 1P Pride alone (clean likely-bot credit, no other attacker visible).

**6. PATTERNS.** Stone-keeping again splits sharply by outcome (lost=0 win vs lost=7 loss). Exact frame(s) where the 7 stones come off: not visible at 1fps.

**7. Vs leg88.** Leg88's loss showed zero back-off from an opponent's transform; this leg shows a real instance of avoiding one (Ryoma's blast on Accel) — a step in the right direction — but the no-retreat-at-low-health pattern from leg88 still repeats at the very end.

**8. SUGGESTION / TO VERIFY.** Suggestion: add an explicit low-health disengage bias, since the bot held position at a sliver of health for over a second before dying. Verify via hit log: what actually lands the killing blow at abs~162s (Pride, Ryoma, or environmental) and whether the "1 stone held" reading at t2:30-32 is real or a HUD-icon artifact.

THREE-LINE SUMMARY:
Loss: bot grabbed 9 stones early but gave back 7, avoided one opponent transform outright, then stalled at critical health next to two opponents and died with the attacker uncertain.
Win: two bot transforms did all the work — a double-KO on Ryoma+Accel, then a clean solo finish on Pride — for only 6% health lost and zero stones dropped.
Vs leg88: first sign of the bot dodging an opponent's transform instead of standing in it, but it still won't retreat once critically low.
