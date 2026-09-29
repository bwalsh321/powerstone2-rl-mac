# Scouting report — league leg 97 (Desert Area)

**Unfilmed wins (rounds 2-3, not scouted).** Round 2: forms=3/1, dmg +6.00/-0.93, picked=10 lost=2, opp=9(-5), chests=21(4), len=684 — same transform/stone-retention line as win_ep01 but a longer round and more damage taken. Round 3: forms=2/1, dmg +6.00/-0.33, picked=4 lost=0, opp=12(-9), chests=22(3), len=592 — perfect stone retention but far fewer pickups than the other two wins.

**WIN (win_ep01, round 1, 0-70s).** forms=3/1, picked=10 lost=2, dmg +6.00/-0.20 (~20% health lost), a fast 409-step round. Bot opens alone at a cactus (sheet001 t00-03) before the ACTION! banner (t04), then engages the trio. Pride (1P) is already critical by sheet003 t26 and X'd by sheet005 t49 — first out. The bot's own fusion swarm (rainbow HUD, sheet003 t28-31) is the first visible transform; two more follow (sheet004 t44-47, sheet005/006 t52-59). Ryoma (3P) is flagged "HELP" repeatedly through the last12s strip while alone; both remaining opponents go down within the final 1.5s of the strip (t10.75-11.75, two X marks) for a 3-0 sweep on the bot's three transforms.

**LOSS (loss_ep04, round 4, 278-359s).** forms=1/1, picked=5 lost=3, dmg +3.48/-1.00, 487 steps. Bot engages immediately at the ACTION! banner (sheet024 t04:43) with no solo opening period, unlike win_ep01. Pride (1P) is again first out, X'd by sheet027 t05:12-13. The bot's one transform swarm fires around sheet026 t05:11. In the last12s strip both ENEMY tags appear beside the bot at t01.75-02.75 (double-teamed), then continuous ring/impact effects run from t04.50 through the killing explosion at t11.75 — roughly 7s of forced-animation juggle, so "uncertain (forced animation)," not evidence of no back-off; the seconds just before the juggle starts are not clearly resolvable at 4fps.

**Passive-state check.** Third leg with a death costing half a win, and this checkpoint scores 30.4% on the 500-round eval of this state. Filmed engagement does not look more passive than earlier legs: win_ep01's picked=10/forms=3/1 matches leg96's win_ep03 (picked=10, forms=3/1) almost exactly; chests=18(1) here vs 21(4)/22(3) in the two unfilmed wins is the low end but not idle. The loss's picked=5/chests=9(1) is the leanest of the four rounds, echoing leg96's loss (picked=4, chests=17(1)) rather than showing new passivity tied to this state.

**Low health / caution.** No stretch in either filmed episode shows the bot visibly in control (walking/attacking) beside an active opponent special at critical health; the loss's entire critical-health stretch (last12s t04.50-11.75) is forced-animation juggle, so no "no back-off" call can be made this leg.

**Stones.** Bot holds stones well when it wins (win_ep01 picked 10 lost 2, held 80%; unfilmed wins held 80% and 100%) but bleeds them in the loss (picked 5 lost 3, held only 40%) — same split as leg96 (win held 80%, loss net negative).

**Vs leg96.** Leg96's loss had a clear no-back-off call (bot in control beside an active attacker before the kill); leg97's loss instead spends its whole critical-health window in a forced juggle, so this leg neither confirms nor refutes that caution pattern — one fewer usable data point, not a behavior change.

**Suggest / verify.** Suggestion: unchanged from leg96 (move away when in control at critical health) — this leg's loss has no control-window example to test it against. Verify: whether the last12s double-ENEMY cluster (t01.75-02.75) is the start of the double-team that leads into the juggle, or a separate earlier exchange — not resolvable at 4fps.

THREE-LINE SUMMARY:
Win: bot opened alone, then landed all three of its own fusion transforms to sweep Pride, Ryoma, and Accel in turn — forms 3/1, picked 10 lost 2, only 20% health lost, a fast 409-step round.
Loss: bot engaged immediately with no opening period, got double-teamed, then spent roughly 7 of its final 12 seconds in a forced hit-stun juggle before dying — forms 1/1, picked 5 lost 3, no back-off call possible (forced animation).
Context: third leg with a death costing half a win at a 30.4%-eval checkpoint; filmed engagement (stones, transforms) matches leg95-96 levels rather than looking more passive, and stone retention still splits clean win / bled loss.
