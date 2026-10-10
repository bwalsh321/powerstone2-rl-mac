# Next leg changes (queue) — kept current by the Ryzen session

Last updated: Oct 7 2026, 9:40 pm EDT. Current recipe on the Ryzen: vision (obs v4 + OBJ_GRID_N=208), taps, learner
KL fix (PS2_PPO_KL_REF=prox), recent-only opponent pool (legs 113+), training slots 30-43 + 50-68, no DAgger.
Reads: vision legs 134-138 = 44.6% lv8mix; + pool/mix legs 139-142 = 47.6% (142 = 51.6%, the record).

## NOW RUNNING FROM LEG 157 (set Oct 10, 8:25 am): practice start points (drill resets), 3-leg read (157-159)

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

## Side project (M2): hunter bot

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
