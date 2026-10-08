# Next leg changes (queue) — kept current by the Ryzen session

Last updated: Oct 7 2026, 9:40 pm EDT. Current recipe on the Ryzen: vision (obs v4 + OBJ_GRID_N=208), taps, learner
KL fix (PS2_PPO_KL_REF=prox), recent-only opponent pool (legs 113+), training slots 30-43 + 50-68, no DAgger.
Last 3-leg reads: vision legs 134-138 = 44.6% lv8mix; + pool/mix legs 139-141 = 46.2%.

## NOW RUNNING FROM LEG 143 (set Oct 7, 9:50 pm): "reward cleanup" bundle, one 3-leg read (legs 143-145)

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

## Later (from the Oct 6 audit)
- Frame stack 7 -> 2 (the LSTM may make it redundant; model shape changes, own read).
- Second sealed held-out lineup set (Desert, new 3-CPU lineups) for confirming big claims.
- Scout upgrades: count double jumps / taps per episode in the log; 15-30 fps clips around events; scout a
  held-out lineup.
- Cross-machine calibration (grade an M4 leg on the Ryzen).
- Fresh drills under vision for Blake (DAgger stays off; idea: use drill states as RL start points, no imitation).
- Cleanup: disk pruning (~2.5 GB/day), dead reward code, gym warnings, stale docs.

## Done recently (for context)
- Grading upgrades (Oct 7): same 1000 start points every leg (paired), distinct-episode count, hold gate on a
  6-point drop below the best of the last 5 legs or <600 distinct rounds.
- Relay: relay_boot.sh (@reboot) + relay_alert.sh (15-min watchdog -> claude_bridge/ALERT.txt).
- DAgger v1/v2 tried and turned off (both cost 6-15 points).
