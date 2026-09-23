# Scouting report — league leg 64 (Desert Area)

**1. LOSS (ep01, 0:00–1:09)**
Opens isolated at the left edge again (intro 0:00, ACTION! 0:04); bot takes ~7s to close on the Ryoma/Accel/Pride cluster near the cacti (reached ~0:08–0:11), reverting to leg61/62's slow close rather than leg63's ~1s. From 0:12 it's a continuous 4-way scrum over chests/gems (0:13, 0:17–19, 0:38, 0:44–47) with two enemy missile/robot-swarm transforms visible (0:49–50, 0:56), matching forms=1/3 opp-side; the bot's own single transform isn't clearly identifiable (possible white-ring effect ~0:38 — not visible at 1fps to confirm). A "HELP" tag appears on/near the bot at 0:57 next to a purple gem, a likely double-team moment. Health stays near-full through 0:06; the death itself is a blind window — a blue crystalline explosion hits at 0:07–0:08, then by 0:09 the screen cuts to a solo no-HUD shot with no visible gradual bar drain, so like leg63 this reads as a possible instant/environmental KO rather than a health-drain death.

**2. WIN (ep02, 1:12–2:43, continuous from the loss episode)**
Same isolated-edge opening (bot alone 1:12, ACTION! 1:13) and ~7s close to the group by 1:19–20. From 1:24 the fight moves into a rockier/watery sub-area with heavy stone traffic (hammer item 1:45–53, thrown boulder 1:56/1:59, chests everywhere) — stones picked=8 vs lost=3, opp stones down 7, matching the lopsided win. Accel (4P) is KO'd first, ~2:15–16, in a flame/explosion burst with the bot tagged "2P" immediately adjacent — plausibly the bot's kill. Ryoma (3P) goes down ~2:17–18 near a cactus with a "HELP" tag on screen but no clear attacker visible. From 2:19 it's Pride (1P) vs. the bot alone for the rest of the clip; the bot shows a wing-like transform aura ~2:37–38 (2nd of forms=2/1) then a gold ring aura 2:40–43 while chasing a fleeing Pride — the finishing KO happens after the last sampled frame, off-camera.

**3. PATTERNS**
- Round-opening isolation at a map edge, now 4 legs running (61,62,63,64), in both episodes this leg.
- Bot flashes repeated "HELP" tags through the back half of the win episode (2:16–2:39) even while winning — chased/ganged even in a round it ultimately takes.
- Neither the loss's KO nor the win's final (Pride) KO is visible at 1fps — both land strictly after the last useful frame.
- Not visible at 1fps: bot's own transform trigger in the loss ep, the attacker for Ryoma's KO in the win ep, and per-tick health around either blind KO window.

**4. SUGGESTION / TO VERIFY**
Compared to leg63: edge-isolation and the "invisible final KO" both repeat unchanged, but close speed reverted to leg61/62's slow ~7s instead of leg63's fast ~1s — no consistent fix for either issue yet.
Suggestion: since neither slow nor fast closing changed the loss/win split, target the spawn-time isolation itself (positioning bias toward the cluster at round start) rather than tuning post-spawn movement speed.
Verify: pull per-tick health + attacker logs for loss ep01 0:06–0:09 (instant/environmental death vs. off-fps drain) and win ep02 2:14–2:18 (confirm the bot lands the Accel KO).
