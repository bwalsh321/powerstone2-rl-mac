# Scouting report — league leg 90 (Desert Area)

**1. WIN (win_ep01, round 1, 0-106s).** forms=2/1, dmg +6.00/-0.33 (33% health lost), picked=7 lost=0, stonev=299. Bot's fusion form is already up by sheet005 t00:35 (gold mech, beam fire hitting 3P Ryoma) and still active at sheet006 t01:00 firing a rocket; 1P Pride's health crashes to a sliver and shows a red X (dead) by sheet006 t01:04 — likely bot (swarm). A long, clean round: 0 stones dropped the entire 106s despite the heaviest health cost seen yet.

**2. LOSS (loss_ep02, round 2, 106-177s).** forms=1/1, picked=4 lost=2, dmg +3.54/-1.00, stonev=160. Bot dies at last12s-strip t11.000 (abs~176s) — the HUD red X lands on 2P's own portrait, not an opponent's — with 1P at ~55% health, 3P ~70%, 4P full, all three clustered on it per sheet014/015's t2:30-2:56 scrum — uncertain single attacker, three opponents adjacent.

**3. Backs off from an opponent's special/transform?** Mixed, new this leg. Sheet014 t2:42-2:45: bot holds back near a cactus while Pride and Accel fight each other, staying out of that exchange entirely — a real instance of disengaging from a fight that isn't its own. But sheet012 t2:21-2:23: it stays in melee range on Accel while a fire-wielding Pride closes from the side, and 2P's bar shows a fresh damage flash right as the flame animation plays beside it at t2:23 — no retreat from that one.

**4. Cautious when low on health?** Not demonstrated this leg. The last12s strip never shows 2P's bar down to a bare sliver before the death frame — it's still a solid partial yellow at t10.750, one tile before the X — so the death reads as a sudden multi-opponent collapse (see #2), not a slow low-health stall like leg89's.

**5. Keeps stones after being hit?** Same split as leg89: clean in the win (lost=0 of 7), leaky in the loss (lost=2 of 4). Notably this loss round grabbed far fewer stones overall (4 vs leg89's 9) and lost a smaller fraction (2 vs 7) — but far fewer stones were in play too (chests=12(1) here vs richer arenas). Exact loss frames not resolvable at 1fps.

**6. PATTERNS.** Good: transform timing converts straight into a KO with zero stones dropped in the win, and the new avoidance of the Pride/Accel scrap in the loss. Bad: still parks in front of Pride's fire attack at close range (#3), and the win now costs 33% health vs leg89's 6% for the same lost=0 outcome — winning "harder," not safer.

**7. Vs leg89.** Same lost=0 stone discipline in the win, but against a real opponent transform this time (forms=2/1 vs leg89's 2/0) it cost 33% health instead of 6%. The loss again ends in a multi-opponent cluster with an uncertain killer, matching leg89 — but leg90 adds one genuine new behavior, disengaging from a fight it's not part of (#3), not seen in leg89.

**8. SUGGESTION / TO VERIFY.** Suggestion: the higher death penalty hasn't reduced health lost in a WIN round — check whether the wider special-damage penalty is discouraging retreat as intended. Verify via hit log: what actually kills the bot at abs~176s, and whether the t2:23 fire contact was a real hit or a HUD-flash artifact.

THREE-LINE SUMMARY:
Win: the bot's fusion form scored a clean missile-swarm KO on Pride and kept all 7 stones, but burned 33% health doing it — far costlier than leg89's 6%-health win.
Loss: it showed a new trick, holding back from a Pride-vs-Accel scrap that wasn't its fight, but still walked into a fire attack up close and died in a three-opponent cluster with no clear killer.
Vs leg89: stone-keeping discipline held steady and a first real disengage-from-others'-fight appeared, but winning now costs much more health than it used to.
