# Scouting report — league leg 86 (Desert Area)

**1. LOSS (loss_ep01, round 1 of 4, video 0-112s)**
Bot (2P) spawns alone by the cactus/rock spawn (sheet001 t0:00); Pride/Ryoma/Accel converge and ACTION! hits at t0:04, and 1P (Pride) is first eliminated early (X on 1P bar by sheet004 t0:17-19). Bot fires its own robot-swarm fusion at t0:32 (sheet003, rainbow gauge t0:26-31 into swarm) — one of forms=3 bot transforms. From t1:36-1:47 (sheet009) a white crescent-slash effect plays on an "ENEMY" tag while 2P stays adjacent fighting rather than disengaging (no retreat movement visible at 1fps) — one of forms=2 opponent transforms, bot does not back off. 3P (Ryoma) goes down by sheet010 t1:51, leaving 2P and 4P (Accel); the last12s strip shows the bot juggled in a multi-hit combo (repeated "HELP"/"ENEMY" tags, hit-counter overlay descending 8→2 from strip 7.5-11s) with no fusion-swarm graphic at the kill — reads as double-teamed, not a special-attack punish. Bot dies (dmg -1.00) but picked=8/lost=0 — it keeps all its stones through the death. Stats: dmg+5.87/-1.00, picked=8/lost=0, opp=10(-7), forms=3/2, chests=16(1), stonev=346, dmgF=3.95.

**2. WIN (win_ep04, round 4 of 4, video 248-349s)**
Bot fights alone early against 1P near the cliff perch (sheet021 t4:00-4:07, HELP tag t4:07), survives to ACTION! reset at t4:12 for the final push. Bot's own fusion swarm fires twice (rainbow gauge + mech icon at sheet024 t4:29-31; second swarm finishes the round in the last12s strip at ~8.25-8.75s/real t5:47, "2P" tag inside the blast, 1P prone with HELP tag underneath) — both bot transforms (forms=2) net kills. An opponent ice-block transform appears near t5:38-43 (sheet029/030, light-blue frozen effect tagged ENEMY); the bot's "2P" tag sits a cactus-width away rather than on top of it (sheet030 t5:42) — a clearer back-off than in the loss. 3P and 4P both show X by sheet028 t5:35; bot wins with 1P dead too by the final swarm. Bot loses 3 stones despite winning (picked=8/lost=3) — the new stone-knock-off penalty didn't prevent losses here. Stats: dmg+6.00/-0.73, picked=8/lost=3, opp=17(-10), forms=2/2, chests=15(2), stonev=212, dmgF=4.30.

**3. PATTERNS**
- Stones-kept-after-hit is inconsistent: 0 lost in the death (loss) vs 3 lost in the win — no clean read on the new penalty from these two rounds alone.
- Back-off-from-transform is inconsistent too: bot stays adjacent to an opponent's crescent-slash effect in the loss (sheet009 t1:36-47) but keeps distance from an opponent's ice effect in the win (sheet030 t5:42) — one data point each way, "not visible at 1fps" for finer movement.
- vs leg85: leg85's loss was a scrum-finish with no back-off evidence at all and the worst stone economy seen (picked=1/lost=2); leg86's loss is also a multi-hit/double-team finish but with picked=8/lost=0 — stone economy improved, death shape unchanged (no disengage in either leg's loss).

**4. SUGGESTION / TO VERIFY**
Suggestion: check whether the bot can break off the t1:36-47 (loss) juggle chain instead of continuing to trade next to the opponent's transform.
Verify: via hit log, confirm whether the loss round's final blow (~1:51-52) was a normal combo (as the strip suggests) or a missed swarm credit, and which opponent(s) landed it.

THREE-LINE SUMMARY:
Loss: bot juggled/double-teamed to death near an opponent's transform without backing off, but kept all its stones (lost=0).
Win: bot's own fusion swarm scored the final KO twice; it kept more distance from the opponent's ice transform than in the loss, but still lost 3 stones.
Vs leg85: stone economy in the loss round improved a lot (lost=0 vs lost=2), but the no-disengage death pattern is unchanged.
