# Scouting report — league leg 82 (Desert Area)

**1. LOSS (ep01, round 1 of 11, ACTION! ~0:04, video 0-90s)**
Bot spawns alone by a cactus; Pride closes first (0:01-03), then Ryoma and Accel arrive and a four-way scrum drifts across the same cactus-flat/rocky-ridge/pool terrain as leg81. The bot transforms once (~0:36-0:38, grey missile/plane swarm, forms=1/2) with no kill confirmed at 1fps; a second, opponent-side transform (a blue/white spinning burst) engulfs the bot at ~0:52-0:54 and the bot does not back off from it — it's caught and knocked away, health draining, rather than disengaging. In the final 12s (4fps strip) the bot is locked in continuous sword/gunfire exchange with Pride and Ryoma from 9-10.5s; at 10.75-11.0s (round's true end, ~89s) both the bot (2P) and Accel (4P) go down together amid a green swarm-like cluster whose source is not clearly identifiable at 4fps — reads as dying inside a chaotic multi-attacker melee/gunfire scrum rather than one clean special, "uncertain" attribution since Pride and Ryoma are both adjacent. No back-off from any charging/transformed opponent is visible anywhere in the sheets. Stats: dmg+3.75/-1.00, picked=5/lost=3, opp=18(-12), forms=1/2, chests=15(0), stonev=185, dmgF=1.46.

**2. WIN (ep11, round 11 of 11, video 869-960s)**
Same arena, standee at 14:29, ACTION at 14:33, same fixed Pride/Ryoma/Accel roster. The bot transforms three times (forms=3/1, the most this leg) and appears to land all three KOs: Ryoma (3P) dies first in a fiery burst tagged 2P at ~15:11 (~42s in, likely bot); Accel (4P) dies at ~953-954s inside a grey missile/plane swarm beside the 2P tag with no other attacker adjacent (likely bot, swarm); Pride (1P), last opponent standing, dies at ~959-960s (round's end) in a final pink/white burst again beside the 2P tag (likely bot, swarm/finisher) for a clean sweep. The bot takes almost no damage all round (dmg+6.00/-0.58, its lowest loss this leg). Stats: picked=9/lost=1, opp=9(-8), forms=3/1, chests=19(2), stonev=296, dmgF=4.47.

**3. PATTERNS**
- Leg82's training added ten random three-level-8-COM lineups across a quarter of episodes; both scouted rounds still used the fixed Pride/Ryoma/Accel roster, so no lineup-randomization effect is visible here — this eval trio's 31% win rate is the league's highest so far.
- vs leg81: win-round forms is similar (3/1 here vs 3/2 there) but opp stone swing favors the bot more (opp=9(-8) here vs opp=13(-11) there), and win-round damage taken is far lower (-0.58 vs -0.50 is close, but dmgF 4.47 here vs 3.26 there) — a cleaner win overall.
- The loss again ends with no disengage from an active opponent effect (same gap flagged in legs80-81), this time inside a multi-attacker scrum rather than a single identifiable special.
- chests=15(0) loss / 19(2) win: still near-zero proximity credit despite double-digit chest counts, consistent with legs77-81.

**4. SUGGESTION / TO VERIFY**
Suggestion: extend the "adjacent to charging/transformed opponent" flag to also fire during multi-attacker scrums, since the loss round's death involved simultaneous pressure from Pride and Ryoma rather than one clean special.
Verify: via hit log, confirm the bot's own swarm (not an opponent's) landed all three win-round KOs (Ryoma, Accel, Pride), and confirm what actually killed the bot in the loss round's final scrum.
