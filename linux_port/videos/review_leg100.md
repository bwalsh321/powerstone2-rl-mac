# Scouting report — league leg 100 (Desert Area)

**Unfilmed losses (ep02-04).** forms=0/3, 1/4, 1/4 — bot never out-transforms the trio (0-1 bot vs 2-4 opponent transforms each round); dmg dealt only +2.29 (ep02) and +4.61 (ep04), vs +5.21 in ep03.

**LOSS (loss_ep01, 0-81s).** forms=1/2, picked 7 lost 5, dmg +2.63/-1.00, 492 steps. Bot's own transform fires once (rainbow 2P gauge, sheet004 t00:41-43) but the round stays four-way chaotic; two opponent transforms pass nearby (blue beam sheet004 t00:38, fire icon sheet006 t01:09) without the bot resolvably engaging them. From last12s strip t09.5 on, bot is locked in continuous knockdown/explosion/juggle (green/pink rings, "HELP" prompt) through death at strip t11.75 — forced animation throughout, no in-control moment visible beside a live special.

**WIN (win_ep05, 366-454s).** forms=3/0, picked 8 lost 0, dmg +6.60/-0.44, 531 steps, dmgF=5.86. Ryoma (3P) dies ~sheet031 t06:05 (X on 3P bar, cause off-window); Accel (4P) dies ~sheet036 t07:02 (X on 4P bar, also unresolved). Round narrows to bot vs Pride (1P); bot's own missile-swarm transform finishes Pride solo at last12s strip t08.0 (X appears on 1P bar amid the swarm) — a clean bot's-own kill, same pattern as leg99's and leg98's wins.

**Opponent-special avoidance (strict rule).** No frame in either round shows the bot walking/attacking in clear separation from a live opponent special in the seconds before contact: the loss's fatal stretch (strip t09.5-11.75) is continuous forced-animation, so "uncertain," not no-back-off; the win never puts the bot beside an opponent transform at all, since opponents never transformed this round (forms=3/0). Same "no demonstrable no-back-off case" conclusion as leg99.

**Stones.** Loss: picked 7 lost 5 (net +2) vs opp 10(-6) (net +4) — bot loses the stone exchange despite decent pickups. Win: picked 8 lost 0 — bot holds every stone it grabs, vs opp 9(-8) (net +1), a far stronger differential than the loss.

**Chests.** Loss chests=16(0): 16 opened arena-wide, none counted near the bot, despite passing multiple intact chests on-screen (sheet002 t00:09-11, sheet003 t00:16-19, sheet005 t00:48-53) — reads as ignoring nearby chests; not visible at 1fps whether by choice or pressure.

**Vs leg99.** Both legs' losses resolve to forced-animation deaths, not clear no-back-off failures. Leg100's win repeats leg99's "bot's own transform finishes the last opponent solo" pattern, with better stone retention (8-0 here vs 7-2 in leg99) and higher special-attributed damage dealt (dmgF 5.86 vs loss's 0.87).

**Suggest / verify.** Suggestion unchanged: retreat while in control at critical health beside a live special — still unobserved either way this leg. Verify: whether Ryoma's and Accel's deaths in the win (sheet031 t06:05, sheet036 t07:02) were bot kills or off-window opponent-on-opponent — not resolvable from these sheets.

THREE-LINE SUMMARY:
Win: bot's own transform swarm finished Pride solo (last12s t08.0), stones perfect (8 picked, 0 lost), dealt 6.60 vs 0.44 taken.
Loss: one bot transform (sheet004 t00:41) wasn't enough in the four-way scrum; death from strip t09.5 reads as forced-animation, not a clear no-back-off failure.
Context: the three unfilmed losses show the bot chronically out-transformed (0-1 vs 2-4 opponent transforms), matching its low damage dealt in two of them.
