# Scouting report — league leg 104 (Desert Area, trio of level-8 COMs) — first leg trained on the 9950X

**LOSS (loss_ep01, 0-80s, 478 steps).** forms=1/1, picked 7 lost 5, dmg +3.99/-1.00, dmgF=2.11, chests=17(1). Opening: the bot (2P) starts at the left edge by the tall cactus and the trio clusters at the upper right; it closes in by sheet001 t00:05-0:07 and by t00:12-00:16 is carrying a cactus and picking up gems. The bar goes rainbow at sheet002 t00:17-00:19 and a missile swarm fills the screen at t00:20 — likely bot (swarm) — but no opponent is X'd by it (all three bars still live at t00:24+). Accel(4P) goes rainbow at ~t00:58 (forms 1 opp). From t01:03 the bot is double/triple-teamed by Accel, Ryoma(3P) and Pride in a cactus-ringed brawl (sheet006-007 t01:03-01:19); health is low by t01:12 and it is X'd at t01:19 (last12s t10.75) under a "HELP" tag — "uncertain (forced animation)," not "no back-off."

**WIN (win_ep02, 80-158s video clock, 453 steps).** forms=3/1, picked 8 lost 0, dmg +6.00/-0.50, dmgF=4.62, chests=16(0). Bot starts bottom-left, sprints at the trio and stays at near-full health most of the round (bar barely dips; first visible damage ~t02:03 range). Rainbow bar at t01:34 produces a missile swarm (t01:37-01:39) with no KO; rainbow again ~t01:57-02:00 and ~t02:15. KOs: Accel(4P) X'd t02:17 inside a swarm blast with Ryoma adjacent — "uncertain, likely bot (swarm)"; Ryoma(3P) X'd t02:34 right after a close-range swarm (t02:33) — likely bot (swarm); Pride(1P) X'd t02:37 (last12s t10.75-11.0) inside a third swarm, bot standing free, no hit-stun tag, at range — likely bot (swarm). All three KOs follow a bot transform.

**Wins still come from out-transforming the trio.** Differential +2 in the win (3/1) vs 0 in the loss (1/1: both sides transformed but the bot's swarm connected with nothing lethal). Same direction as leg103.

**Opponent-special avoidance (strict rule).** No clear case: the loss's death is a forced-animation chain (t01:12-01:19); no free-control frame next to a telegraphed special is visible at 1 fps, so none is claimed.

**Stones.** Win is net +8 (8/0), the cleanest stone round in recent reviews; loss is net +2 (7/5) with the bot losing stones in the t01:03-01:19 brawl (not visible at 1 fps which hits shed them).

**Patterns.** Chests ignored again: chests sit near the bot at loss t00:09-00:12 and t00:40-00:43 and win t02:01, t02:31-02:34 (loss 17(1), win 16(0)). Loss t00:48-00:59 shows the bot hugging cactus pillars beside Ryoma/Pride with little visible damage dealt; Pride's bar is already low from ~t00:36 and he is never finished in the loss (not visible at 1 fps whether the bot could reach him). Win: the bot idles near a bomb/chest at t01:57-02:01 before the next engage — brief, not costly.

**Vs leg103.** Same shape (out-transform differential tracks outcome, loss ends in a forced chain, finishing happens when fights thin out); difference is leg104's win has zero stones lost and all three KOs swarm-credited rather than a launcher finish, and the loss is much shorter (478 vs 759 steps) with no opponent KO.

**Suggestion:** when the bot is at low health and 2+ opponents converge (loss t01:03-01:12), disengage toward open ground rather than keep brawling beside cactus clusters, and use the transform earlier than the opponent (Accel went rainbow at t00:58, bot had already burned its swarm at t00:20 with no KO). **Verify:** count in a batch of rounds how many bot swarms (transforms) result in a KO within 5 s versus none, since this loss spent its one transform with no kill.

THREE-LINE SUMMARY:
Loss (forms 1/1, 478 steps): the bot's early swarm at t00:20 killed nobody, then Accel, Ryoma and Pride triple-teamed it and it fell at t01:19 in a forced-animation chain.
Win (forms 3/1): three bot transforms each produced a likely-bot swarm KO (Accel t02:17, Ryoma t02:34, Pride t02:37) while the bot lost no stones and took almost no damage.
Pattern: transforms decide the round again, and chests plus low-health disengagement are still ignored.
