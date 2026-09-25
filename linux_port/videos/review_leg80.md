# Scouting report — league leg 80 (Desert Area)

**1. LOSS (ep01, round 1 of 3, ACTION! ~0:04, video 0-86s)**
Bot spawns alone by a giant cactus; Pride (1P) is first to close in (~0:01-03), then Ryoma (3P) and Accel (4P) arrive together (~0:04) and the three-way scrum forms on the sandy/cactus flat before drifting toward the rockier water-fringed stretch (~1:00+, same terrain leg79 used). The bot never transforms this round (forms=0/3) — a robot/plane-swarm-shaped blast at ~1:17-18 (strip 3.25-4.25s) must therefore be one of the opponents' 3 transforms, not Falcon's own, despite the look. In the final-12s window Pride shows a lock-on-style ring (yellow then pink, ~1:23.5-24.25) and fires a beam/dash attack while the bot stays right beside it; the bot dies ~1:25 in the resulting flash with no disengage attempt visible, so this loss ends inside a special, not a melee juggle or idle lull. Stats: dmg+2.61/-1.00, picked=5/lost=6, opp=12(-11), forms=0/3, chests=24(2), stonev=278, dmgF=0.00.

**2. WIN (ep03, round 3 of 3, ACTION! ~3:31, video 207-298s)**
Same scrum reforms on the cactus flat, now littered with turret/cannon hazard props and dense chests; the bot transforms three separate times this round (forms=3/1) against only one opponent transform. Accel (4P) and Ryoma (3P) die within the same half-second (~4:50.25 and ~4:50.5) while flailing in hit-stun/falling animation with no single clean swarm or beam visible — reads as a bot melee combo/AOE, not a special, but the exact blow is unresolvable even at 4fps. Pride (1P), now alone, is chased solo by the bot for the last ~7s (repeated "HELP" tags over Pride from ~4:51 on) and dies ~4:57 engulfed in a grey robot/plane swarm with no other attacker adjacent — per the fusion rule this is likely bot (swarm). Stats: dmg+6.00/-0.83, picked=12/lost=4, opp=12(-11), forms=3/1, chests=15(0), stonev=236, dmgF=4.19.

**3. PATTERNS**
- Leg80 is the second leg (after leg79) on the full level-3/level-8 character set: like leg79's loss, this loss dies inside a charging opponent's special while adjacent with no disengage — same gap, now against Pride instead of Accel.
- forms flips hard vs leg79: this leg's loss has zero bot transforms (0/3, first zero-transform loss in legs76-80) while the win has three (3/1) — the opposite skew from leg79 (loss 1/2, win 2/4).
- Stone economy: loss nets picked5-lost6=-1, the first negative net seen in legs76-79's losses; win nets +8 (12-4), the largest positive net logged yet.
- chests=24(2) loss / 15(0) win: still near-zero proximity credit despite dense chest fields, consistent with legs77-79.

**4. SUGGESTION / TO VERIFY**
Suggestion: extend the leg77-79 "adjacent to a charging/transformed opponent" flag to cover lock-on rings from any character (here Pride's yellow/pink ring), not just Accel's — the bot shows the same no-disengage behavior against a second attacker.
Verify: via hit log, confirm Pride was the attacker on the bot's ~1:25 death, and confirm whether a single bot AOE (vs. two separate hits) killed both Ryoma and Accel at ~4:50.
