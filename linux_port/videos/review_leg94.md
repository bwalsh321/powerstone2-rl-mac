# Scouting report — league leg 94 (Desert Area)

**LOSS (loss_ep01, round 1, 0-64s).** forms=0/2, dmg +1.86/-1.00, picked=2 lost=3, chests=16(0) — bot never transforms while both opponents do, and barely touches the stone economy. 2P is still at full health through last12s-strip t10.750 (sheet006), then the very next sampled frame (strip t11.000, abs~63s) shows a red X on 2P's bar with a "HELP" tag and 1P Pride adjacent — the actual killing hit is not visible in any frame, happening between t10.75 and t11.00.

**WIN (win_ep04, round 4, 310-433s).** forms=3/3, dmg +6.00/-0.69, picked=11 lost=3, opp=14(-10), dmgF=4.10. Bot activates its own transform (golden robot form, sheet031 t6:03, white activation ring), and the resulting missile swarm hits 3P and 4P simultaneously one second later (sheet031 t6:04, both bars crash together). Both are gone by the final 12s (last12s-strip t0.000 already shows 3P and 4P X'd), leaving a clean 1v1 that the bot closes with the same swarm move on 1P Pride at last12s-strip t11.000 — bot's own kill, not "likely," since no other attacker is present.

**The three losses.** dmg dealt jumps after the opener (+1.86 → +6.36 → +5.51) and forms (bot/opp) go 0/2 → 2/3 → 1/1, but dmg taken is pegged at exactly -1.00 in all three and the bot dies every round regardless of the better offense.

**Good / bad.** Good: once transformed, the bot's own swarm reliably erases one or two opponents at a time (sheet031 t6:04; last12s t11.000), and pickups are strong in 2 of 4 rounds (picked=11 in both loss_ep02 and win_ep04). Bad: loss_ep01 shows almost no stone engagement (picked=2, chests 0(0) near bot) and forms=0/2 — the bot never got a transform online before dying.

**Back-off / stones.** loss_ep01: not demonstrable — the death is off-frame and paired with a "HELP" tag, so per the Sep 28 rule this is "uncertain (forced animation)," not "no back-off." win_ep04: the one opponent transform the bot is near, 4P's green flying robot (sheet033 t6:24-6:26), shows 2P already tagged at the far corner of the frame (sheet033 t6:24) — no back-off failure observed. Stones: win_ep04 holds 8 of 11 picked; loss_ep01 never picks up enough (2) to judge holding.

**Vs leg93.** Same finishing mechanism (bot's own fusion swarm) but this leg's win is a clean solo kill on the last opponent (last12s t11.000) rather than leg93's simultaneous 3-opponent kill, and stone retention improved (8/11 held vs leg93's 5/10).

THREE-LINE SUMMARY:
Win (round 4): the bot transformed on its own, swarmed 3P and 4P together mid-round (sheet031 t6:04), then soloed 1P Pride with the same swarm one second before time ran out.
Losses (rounds 1-3): damage output and transform count rose after the opener, but the bot still died every round, and loss 1's death itself happens off-frame with no visible cause.
Vs leg93 / stones: the finishing move is unchanged (own fusion swarm), but stone retention improved this leg (8/11 held vs 5/10).
