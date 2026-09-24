# Scouting report — league leg 76 (Desert Area)

**1. LOSS (ep03, round 3 of 3, ACTION! ~0:05, video 199-305s)**
Same cactus-scrum open, bot stays in the scrum with Ryoma/Pride/Accel rather than pulling back. Accel (4P) goes down first (bar X by ~3:26-27), Pride (1P) fades from repeated hits and is X by ~5:00, attackers unresolvable at 1fps for both. From ~5:08 (round-clock) Ryoma (3P, blue) puts up a crescent-moon/sword special that forms directly on top of the "2P" tag; the bot is shown tagged inside/adjacent to the ring for ~2.5s straight through the final 4fps window and the red-X KO lands on the bot at the end of that same special, with no separation attempt visible. The bot's own rainbow gauge (2nd transform, forms=2) is lit for this whole closing stretch but never produces a visible swarm before it dies. Stats: dmg+5.15/-1.00, picked=8/lost=3, opp=16(-12), chests=22(2), dmgF=2.77.

**2. WIN (ep01, round 1 of 3, ACTION! ~0:04, video 0-113s)**
Same scrum open in a chest-heavy patch of the map. Accel (4P) is X by ~1:13, attacker unresolvable. Late in the round the bot's own missile/robot swarm erupts twice, each time with the "2P" tag inside it: the first (~1:47-48 round-clock) is immediately followed by Ryoma's (3P) bar going X, the second (~1:50-51) by a screen-wide red-X and Pride's (1P) bar going X, ending the round with a victory pose at ~1:53. Both final KOs are cleanly credited to the bot's own fusion special per the swarm rule. Stats: dmg+6.23/-0.73, picked=11/lost=3, opp=15(-10), chests=29(1), dmgF=3.88.

**3. PATTERNS**
- Third leg with opponent hit-stun/attack/transform/special-volley states visible, level-8 score down three legs straight: the loss again ends inside an opponent's special with no disengage (Ryoma's crescent-moon here vs Accel's fire-spiral in leg75) — same failure, different attacker. The win is new versus leg75: both closing KOs are now clearly resolved as the bot's own swarm, where leg75's win couldn't even resolve its final KO in the 4fps strip.
- forms=3/3 (win) vs forms=2/2 (loss): opponents matched the bot's transform count in both rounds this leg, unlike leg75 where the loss's opponents out-transformed the bot 3:1.
- chests=29(1) win / 22(2) loss: still near-zero near-bot chest credit despite standing in dense chest clusters all round — not visible at 1fps whether the bot opens any itself.
- Stone economy: win picked=11/lost=3 (net+8) vs loss picked=8/lost=3 (net+5) — smaller win/loss gap than leg75's (+7 vs +2), i.e. the loss's stone economy wasn't the main problem this time.

**4. SUGGESTION / TO VERIFY**
Vs leg75: leg75's loss ended inside Accel's telegraphed fire-spiral with no disengage; leg76's loss repeats that exact failure against a different opponent (Ryoma's crescent-moon), so the disengage gap looks attacker-agnostic rather than tied to one opponent's move.
Suggestion: same as leg75 — treat any opponent special forming on/around the bot's own position as a hard disengage cue, regardless of which opponent casts it, since the bot has now died inside two different opponents' specials in a row without moving away.
Verify: confirm via hit log that Ryoma's crescent-moon (not a stray Pride hit, since Pride was already down by ~5:00) is what lands the loss's final blow, and separately whether the bot's own forms=2 transform in the loss ever fires a swarm before death or is wasted entirely.
