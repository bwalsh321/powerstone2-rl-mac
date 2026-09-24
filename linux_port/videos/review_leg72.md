# Scouting report — league leg 72 (Desert Area)

**1. LOSS (ep01, round 1 of 5, 0:00–1:27 video time)**
Standard open: bot alone by the cactus, ACTION! at 0:04, immediately drawn into the chest scrum with all 3 opponents. Bot closes its own transform early (~0:16-17) and stays transformed a long ~30s (rainbow gauge steady through ~0:47), firing its own missile/robot swarm two-plus times (0:19, 0:22, ~0:43) — most of it whiffs, but the last one kills Accel (4P, confirmed dead by 0:47), a bot-credited kill per the fusion rule. Stones/dmg for the round: picked=7/lost=2, opp=10(-4), dmg+4.70/-1.00, forms=2/2, chests=15(0) — numerically the best of the four losses. Bot then fights Pride and Ryoma alone for ~40s with no second transform. Death: at ~1:24 Pride's own gauge fills rainbow (opponent transform, the fusion-swarm rule correctly assigns this to Pride, not the bot), Pride's swarm fires at ~1:26 and the bot's bar X's out that same instant, with Ryoma (3P, still full health) tagged adjacent throughout — bot dies inside an opponent's own special, not its own.

**2. WIN (ep05, round 5 of 5, 4:22–5:44 video time)**
Same chest-scrum open. Pride and Accel are both dead by 5:00 — cause/order not visible at 1 fps in the 4:48-4:59 window. From 5:00 the bot spends a full ~44s solo-chasing the last opponent, Ryoma, across the map while continuously transformed (rainbow gauge steady from at least 5:40 to the end). The chase ends with the bot's own missile/robot swarm landing on Ryoma at rel ~11.0s in the last-12s strip (video ~5:44) — bot's own fusion special, credited to the bot, sealing the win. Stats: picked=9/lost=2, opp=3(-4), dmg+6.00/-0.40, forms=3/0 (no opponent transform fired all round), chests=11(2) — the best dmgF (4.74) of all 5 rounds.

**3. PATTERNS**
- forms=2/2 in the loss vs 3/0 in the win: opponents got zero transforms off in the win but two in the loss, one of which killed the bot — opponent transform activity tracks the outcome this leg.
- The loss's first bot transform ran ~30s but only converted to one kill despite firing its swarm several times — a partially wasted transform window.
- The win's 44s chase-to-finish on a lone Ryoma is the opposite of leg71's flagged "ignored a low opponent" failure — good finishing behavior this leg.

**4. SUGGESTION / TO VERIFY**
Vs leg71: leg71's loss died to a double-team and an unfinished low Pride; this leg's loss instead dies directly inside an opponent's (Pride's) own transform swarm while standing adjacent to it — a different failure mode, not a repeat.
Suggestion: back off or interrupt when an adjacent opponent's transform gauge fills (visibly rainbow ~1-2s before the swarm fires), rather than staying in range through the wind-up.
Verify: confirm via hit/combat log whether Ryoma also landed damage during the loss's fatal swarm at ~1:26, to check if it was Pride alone or a joint hit.
