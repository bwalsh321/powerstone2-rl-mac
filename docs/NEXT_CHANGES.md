# Next leg changes (queue) — kept current by the Ryzen session

Last updated: Oct 14 2026, 9 am EDT. Full session state: docs/SESSION_HANDOFF_RYZEN.md.
KL fix (PS2_PPO_KL_REF=prox), recent-only opponent pool (legs 113+), training slots 30-43 + 50-68, no DAgger.
Reads: vision legs 134-138 = 44.6% lv8mix; + pool/mix legs 139-142 = 47.6% (142 = 51.6%, the record).

## QUEUED BY BLAKE (Oct 13): learning rate -> frame stack -> bigger network, one at a time, 3-leg reads

Hunters at 50% (legs 165-167): sampled lv8mix 57.2 / 51.0 / 49.6 (168 = 52.2), hunted 17.5 / 11.4 / 15.4: no lasting
gain over ~50 / ~12 before. Hunters stay at 50% (not changed).
RESULT: lr 5e-5 KEPT. Legs 170-172 sampled 56.9 / 61.3 / 57.5 = 58.6 vs 52.0 (166-169); top-move 68.0 / 64.6 (records).
2. **NOW: frame stack 7 -> 2 (fold) from leg 174** (league_env.txt PS2_OBS_STACK=2 + `174 framestack2fold` in
   league_surgery.txt; previous: claude_bridge/league_env_leg173.txt). Fold = dropped frames' weights added onto lag 1
   (51% same top action as the parent vs 31% for plain drop). Read 174-176 vs 170-173 (sampled).
1. (done) learning rate 1e-4 -> 5e-5 from leg 170 (league_optim.txt; previous: claude_bridge/league_optim_leg169.txt).
   Read legs 170-172 sampled lv8mix vs 166-169 (~51). Watch entropy (rose to 2.04 at 167, back to 1.75 at 168).
2. Frame stack 7 -> 2 (model input shape changes; own read).
RESULT: frame stack 2 (fold) KEPT. Legs 174-176 = 57.4 / 61.9 / 61.4 (60.2 on the same 1000 games vs 59.8 for 171-173);
   hunted ~20 vs ~16.5; legs ~20% longer (more gradient steps before the KL stop).
RESULT: 512 KEPT. Legs 179-181 = 64.4 / 62.8 / 64.8 = 64.0 vs 60.9 (176-178) on the same 1000 games; legs ~4 h.
3. (done) bigger network, MLP 256 -> 512 from leg 179 (league_env.txt PS2_NET_WIDTH=512 + `179 widen512`; previous:
   claude_bridge/league_env_leg178.txt; built (agent, worktree .claude/worktrees/bignet, branch bignet): function-preserving
   widening 256 -> 512 (Net2Net style), speed cost measured before turn-on. The old 512-wide test predates memory and vision.
RESULT (Oct 19): lr 1.25e-5 NEUTRAL, kept (no harm). lv8mix 202-204 = 69.8 vs 70.7 (199-201) on the same games;
sealed Desert 204 = 70.7 vs 200 = 72.0. The lr lever looks spent. Next: the adaptive handicap (warlock.ai idea; needs
code: lower the bot's start health while its training win rate is high), or more lineup/stage diversity. Blake decides
after vacation.
(done) learning rate 2.5e-5 -> 1.25e-5 from leg 202 (previous:
claude_bridge/league_optim_leg201.txt). Main test flat since 191-193 (69.7); read 202-204 on lv8mix + sealed.
RESULT: pool recent-only KEPT. lv8mix even (198-200 = 69.3 vs 69.6), but sealed Desert 196 = 66.0 -> 198 = 71.3,
200 = 72.0 (unseen lineups). Old snapshots stay in pool_league_archive/.
(done) opponent pool recent-only from leg 198. Pool snapshots from legs <170 (513 of 741
files) MOVED to pool_league_archive/ in the battery window after leg 197 trains (no deletes; move back to undo).
Plateau: the 3-leg high is 69.7 (191-193), then 68.7 / 69.4 / 68.4 (leg 196 = 68.0). Read 198-200 on lv8mix AND the
sealed set (sealed_grade.sh, branch sealed-ent; baseline leg 196 running).
Sealed set (Oct 17, slots 95-99: 3 new Desert lineups + Blue Sky + Dark Castle), Desert 95-97:
leg 169 = 54.7, 178 = 63.7, 193 = 64.0; new stages ~2% (the bot never trains off Desert).
So 169 -> 178 generalized (+9), but 178 -> 193 (+10 on lv8mix) did not show on unseen lineups.
RESULT: lr 2.5e-5 KEPT. Legs 191-193 = 71.1 / 66.8 / 71.2 = 69.7 vs 66.0 (187-190) on the same 1000 games; top-move
   74.4 / 77.4 / 73.4. Riding until the next plateau; then LSTM 256 (vacation plan step 4).
4. (done) learning rate 5e-5 -> 2.5e-5 from leg 191. 512 rode 179-190: 3-leg highs 64.0 ->
   68.4 (185-187), then 68.1, 66.3 (leg 189 = 64.5); leg 190 would need 74.6 to set a new high. Previous:
   claude_bridge/league_optim_leg190.txt. Read 191-193 vs 187-190 (sampled ~66-67). (Was: another learning-rate cut (5e-5 -> 2.5e-5) whenever the grade goes flat for 3-4 legs again (Blake, Oct 13:
   lr 1e-4 -> 5e-5 took sampled 52 -> 59; not touched while another change is being read).
Later ideas: a small reward for finishing low-health opponents / not standing next to transformed ones (scouts keep
showing both; reward changes have hurt before, leg 143).

## IDEA QUEUE from warlock.ai's Warcraft III agent (Oct 18, https://warlock.ai/blog/warcraftsim-1/)
1. **Adaptive handicap to keep training ~50/50.** They taxed the built-in AI's resources after losses and untaxed
   it after wins. Our 3-CPU training win rate is 66% and lv8 is the CPU max, so handicap the BOT instead: lower its
   start health (PS2_START_HEALTH exists) when training win rate is high. Top pick after the current lr read.
2. UPGO credit assignment (algorithm change; later).
3. Throughput: "most of the speed came from removing waste". Profile the learner (now the bottleneck).
Their eval on an unseen map matches our sealed set; their weakness (one strategy, no diversity) matches ours
(Desert-only, familiar lineups).

## TRIED AND TURNED OFF (Oct 10): practice start points (drill resets), legs 157-160

Legs 157-159 = 55.9% vs 153-155 = 56.0% on the same games (738 gained / 743 lost): no effect. Drill rounds stayed
~26% won every leg (normal ~51%): the bot did not learn to get out of those spots. Off from leg 161 (Blake).

Some training rounds start from saved moments where the CURRENT bot (leg 155) was about to lose, harvested on
training lineups 50-68 only (never the graded 90-94), and the bot plays them out with ordinary RL: no imitation,
no reward change (unlike DAgger, which copied Blake's inputs before vision). Target: the KO study's finding that
4 of 5 losses come right after the bot's transforms run out. Flags PS2_DRILL_DIR / PS2_DRILL_P (~0.2), 3-leg read.
Built and merged (2937403): 163 drills from leg 155 (60 losses; 8 s / 4 s before KO + form-end), none from 90-94.
Harvest finding: in 72% of losses an opponent had transformed within 3 s of the KO (the stronger pattern);
only 27% died within 10 s of the bot's own form ending. Training [ep] lines for drill rounds end in drill=...;
exclude them when reading training win rate. Previous settings: claude_bridge/league_env_leg156.txt.
Not planned: a per-KO reward (the KO study showed the bot already lands ~90% of KOs).

## TRIED AND REVERTED (Oct 9): learner batching fixes, legs 149-152

Top-move grade 58.2 / 57.6 / 53.8 / 53.1, but the policy's entropy rose every leg (1.99 -> 2.35, it had been
falling), training win rate on 3-CPU slots fell 52 -> 44%, and the sampled-move grade of 151 was 44.0 vs 145's
54.4. Likely cause: whole-batch advantage normalisation weakened the policy signal relative to the entropy bonus.
Reverted at Blake's call; leg 153 restarts from leg 149 on the 145-148 learner settings. If retried: split clipping
alone, or with a lower ent_coef, and watch entropy + the sampled-move grade. Details of what was built:

Plateau reached: legs 146/147 (55.6/51.7) did not beat leg 145 (56.5, the record). Changes (ppo_train.py, all
flags; flags off was bit-identical in a test): `PS2_PPO_ADV_NORM=global` (normalise advantages over the whole
batch, not per 256-step slice), `PS2_PPO_SPLIT_CLIP=1` (clip policy and critic gradients separately: on real games
the critic's gradient was ~20-32 vs the policy's ~0.7, so the shared clip shrank policy steps ~40x),
`PS2_BATCH_SIZE=1024` in league_optim.txt (was 256). Previous settings: claude_bridge/league_env_leg148.txt and
league_optim_leg148.txt. Read: legs 149-151 vs legs 145-147 on the same 1000 games.

## TRIED AND REVERTED (Oct 8): "reward cleanup" bundle at leg 143

Leg 143 = 40.2% vs leg 142 = 51.6% on the same 1000 games (286 win->loss vs 172 loss->win); slot 91 collapsed
116 -> 30 while slots 90/94 set records. The hold gate stopped the relay; Blake chose to revert. Leg 144 continues
from leg 142 on the leg 142 recipe. If retried, test the three parts one at a time (the stone cap is the most
likely culprit). Bundle details as built:

Built and tested (merge 435901b; receipts in linux_port/receipts/reward_cleanup/), behind flags that default OFF;
turned on in league_env.txt + `143 itememb0` in league_surgery.txt. Previous recipe saved as
claude_bridge/league_env_leg142_poolmix.txt. Measured before the switch: the hit-source pointer resolves ~58% of
hits (the rest fall back to the old guess); learner-credited damage moves ~+21% net; the item surgery changes
2.2% of greedy actions.
1. **Damage credit from the game's own hit-source pointer** (`PS2_DMG_ATTRIB=hitsrc`) instead of the
   "nearest alive seat" guess. The agent first measures how often the two disagree.
2. **Stone-reward cap 19 -> 9** (`PS2_GEM_EP_CAP=9`), so stones can't earn almost as much as a win (+20).
3. **Zero the junk "item" inputs** obs[12..17] (they encode an arena slot, not an item): `PS2_OBS_V4_ITEMEMB=zero`
   plus a one-shot `itememb0` surgery line in league_surgery.txt so behaviour changes as little as possible.

Turn-on steps (once the agent's tests pass and the branch is merged): add the flags to league_env.txt and the
`<N> itememb0` line to league_surgery.txt, between legs (relay scripts only by atomic mv). Read it as a 3-leg pool
against legs 139-141 (46.2%). With paired grading (from leg 142) legs are compared on the same 1000 games.

Grading (Oct 12, Blake): from leg 165 the per-leg lv8mix grade and the hold gate use SAMPLED moves (the way the bot
trains); top-move grades swung +-15 from brittleness (145-148, 163-164). Top-move runs beside each leg (top_grade.sh);
the hunted grade is sampled too. Hold gate: sampled grade more than 6 below the mean of the last 5 sampled grades.

Hunted grade (top-move): 161 = 5.0% -> 162 = 13.6% -> 163 = 13.9% (normal grade steady ~56%). Hunter share raised 0.3 -> 0.5
from leg 165 (Blake, Oct 11). Video of the bot vs hunters: linux_port/record_hunted.py.

## NOW RUNNING FROM LEG 162 (restarted Oct 11, 7 am; 162 on the plain recipe was stopped): hunters in training (PS2_HUNTER_P=0.3), 3-leg read (162-164)

Test result (leg 159, slots 30-43, 280 paired rounds): 40.4% vs two copies of itself, 7.1% vs two hunters.
In training, 30% of the slot 30-43 rounds put hunters (Blake's aimbot ladder retargeted at our bot) in the open
seats. Read on BOTH lv8mix and the new per-leg hunted grade (hunt_grade.sh; baseline = leg 161's hunted grade).
Previous settings: claude_bridge/league_env_leg162.txt.

## (built Oct 10) hunter bot

Plan in docs/HUNTER_PROJECT.md (written for the M2; now built and run on the Ryzen). Note: a 512-wide network was
tried long ago and did worse than 256, so a bigger network is lower on the list.

## (was) Side project (M2): hunter bot

A scripted opponent that only hunts our bot (Blake's aimbot, retargeted): measure how the bot does when it is
not ignored, then maybe train against it. Spec: docs/HUNTER_PROJECT.md. Runs on the M2 (1-2 test legs); the Ryzen is untouched.

## Later (from the Oct 6 audit)
- Frame stack 7 -> 2 (the LSTM may make it redundant; model shape changes, own read).
- Second sealed held-out lineup set (Desert, new 3-CPU lineups) for confirming big claims.
- Scout upgrades: count double jumps / taps per episode in the log; 15-30 fps clips around events; scout a
  held-out lineup.
- Fresh drills under vision for Blake (DAgger stays off; idea: use drill states as RL start points, no imitation).
- Cleanup: disk pruning (~2.5 GB/day), dead reward code, gym warnings, stale docs.

## Done recently (for context)
- Grading upgrades (Oct 7): same 1000 start points every leg (paired), distinct-episode count, hold gate on a
  6-point drop below the best of the last 5 legs or <600 distinct rounds.
- Relay: relay_boot.sh (@reboot) + relay_alert.sh (15-min watchdog -> claude_bridge/ALERT.txt).
- DAgger v1/v2 tried and turned off (both cost 6-15 points).
