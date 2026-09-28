# Scouting report — league leg 93 (Desert Area)

**1. WIN (win_ep01, round 1, 0-79s).** forms=2/1, dmg +6.07/-0.93, picked=10 lost=5, chests=25(1), stonev=308. Bot's own fusion swarm (yellow burst, last12s-strip t6.750-7.250, abs~74s) drops 1P Pride and 4P Accel simultaneously — both show X at strip t7.000 — and a second burst from the same swarm finishes 3P Ryoma at strip t8.000-8.250 (abs~75s): likely bot (swarm) for all three, all down within ~1.5s. Stone retention is worse than leg92's win: half the picked stones are lost (5/10 vs leg92's 1/9).

**2. LOSS (loss_ep03, round 3, 207-255s, the 245-step fast death).** forms=0/0, dmg +1.39/-1.00, picked=0 lost=1, chests=5(0) — bot opens/collects nothing all round. First contact (sheet019, t3:36-3:41 / abs~216-221s) is a non-damaging clinch with 3P Ryoma; 2P's bar is still full. Real damage starts ~22s in when 1P Pride's fire hits (sheet020 t3:53 / abs~233s); by ~33-36s in (sheet021 t4:04-4:07 / abs~244-247s) 3P and 4P are both tagged adjacent (double-teamed). From last12s-strip t8.000 on, 2P is airborne/ragdolled, then shown inside knockdown rings with a "HELP" tag through the X at strip t11.000-11.250 (abs~254-254.25s).

**3. Backs off from an opponent's special (new forced-animation rule applied)?** Not demonstrable either round. Loss: forms=0/0 means no opponent transformed at all this round, and the death itself is the forced-animation sequence described above (ragdoll/knockdown/HELP) — per the Sep 28 rule this is "uncertain (forced animation)," not "no back-off," since 2P is not visibly in control in the seconds before the KO. Win: the lone opponent transform (forms=2/1) isn't identifiable at 1fps, same limitation as leg92.

**4. Holds its stones?** No. Win round loses half of what it picks (5/10, worse than leg92's 1/9); loss round never picks any up (0) to hold in the first place.

**5. PATTERNS.** Loss shows near-total passivity toward stones/chests (picked=0, chests 0 near bot) plus a multi-second non-damaging clinch before any real hit lands — not visible at 1fps whether disengage from that clinch was possible. Win repeats leg92's pattern of the bot's own fusion doing the killing work, but stone economy regressed.

**6. Vs leg92.** Same win mechanism (bot's own fusion swarm kills the last two-plus opponents) but stone retention is worse this leg (5/10 lost vs 1/9). The loss is not a comparable data point under the new rule: leg92's loss showed a live grapple to judge "no back-off" against; this leg's fast loss is forced-animation (ragdoll/knockdown) throughout its final seconds, so no back-off verdict can be assigned.

**7. SUGGESTION / TO VERIFY.** Suggestion: check why picked=0 across a 245-step round — was any stone ever in reach, or did the double-team start before a pickup attempt was possible? Verify via hit log: which of 1P/3P/4P landed the strip-t11.000 killing blow, and whether the win's strip t6.75-8.25 fusion was one continuous swarm or two separate activations.

THREE-LINE SUMMARY:
Win (round 1): bot's own missile-swarm fusion killed all three opponents within about 1.5 seconds of firing, but retention was worse than leg92's win (5 of 10 stones lost vs 1 of 9).
Loss (round 3): a 245-step near-instant death — bot collected zero stones, took its first real damage ~22s in from Pride's fire, got double-teamed by Ryoma and Accel, and the final seconds show it ragdolled/knocked down (forced animation), not choosing to stand its ground.
Vs leg92 / training change: the win still leans entirely on the bot's own fusion to finish fights and stone retention slipped, while the new forced-animation rule means this leg's loss can't be scored for backing off at all.
