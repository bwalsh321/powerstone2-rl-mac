# Scouting report — league leg 92 (Desert Area)

**1. WIN (win_ep01, round 1, 0-75s).** forms=3/1, dmg +6.00/-0.23, picked=9 lost=1, chests=14(0). 1P Pride and 4P Accel both die mid-round (off the last12s window); the filmed final kill is unambiguous — bot's own missile-swarm fusion first tags 3P Ryoma without killing at last12s-strip t04.500-05.500, then a second fusion swarm at the same waterhole finishes Ryoma at strip t11.250 (abs~74s). Only 2P and 3P were alive by then, so no other attacker was possible. Cheap win: 23% health lost, stones kept (lost=1/9).

**2. LOSS (loss_ep02, round 2, 75-198s, the long round).** forms=2/3, dmg +5.08/-1.00, picked=10 lost=5, chests=26(3), stonev=377. Both bot transforms (fusion swarms at abs~1:44 and ~2:42-45) land but don't close out the round. At last12s-strip t09.000 (abs~3:05), 4P Accel's own transform — a green robotic/dragon form — grapples 2P point-blank in a cactus cluster and never releases; 2P's bar drains from full to empty by strip t10.750 and shows X at t11.000, with 3P's "ENEMY" tag adjacent too (double-teamed, second attacker uncertain). Half the picked-up stones are lost (5/10).

**3. Backs off from an opponent's transform?** No. In the loss, 2P is grappled the instant Accel's transform starts (strip t09.000) and stays inside it through the KO two seconds later — no retreat attempt visible. The win's lone opponent transform (forms=3/1) isn't identifiable at 1fps, so no comparison point there.

**4. Cautious at low health?** Not demonstrated. Loss: 2P's bar runs from full to empty across strip t09.000-11.000 while still grappled, no disengage. Win: 2P's own health never drops far (dmg -0.23 total), so low-health behavior isn't tested either way.

**5. Keeps stones after being hit?** Yes in the win, no in the loss — lost=1/9 (11%) in the win vs lost=5/10 (50%) in the loss; the win's retention is close to leg91's win (lost=3/14, 21%), but the loss round bleeds stones just as leg91's losses did.

**6. PATTERNS.** This is the leg where training data first shows fewer deaths/fewer stones lost overall, and stone retention in the win round matches that (lost=1/9). But the two specific behaviors aren't visible in what's filmed: no backing off from Accel's transform (loss), and no low-health caution test in either round — bot converts its own transform into a kill (win) and stands inside the opponent's transform until death (loss).

**7. Vs leg91.** Same shape as leg91: both legs' filmed losses end with 2P standing inside a live opponent transform with zero retreat (leg91: Ryoma's ice, sheet006; leg92: Accel's dragon form, strip t09.000) — the higher death penalty hasn't taught disengagement yet, only better stone retention in the win.

**8. SUGGESTION / TO VERIFY.** Suggestion: since the loss death is a sustained grapple rather than a burst hit, check whether a distance-based disengage trigger even fires against grapple-type opponent transforms. Verify via hit log: who (Accel or Ryoma) landed 2P's killing blow at strip t11.000, and what damaged 3P without killing it at strip t04.5-5.5 in the win.

THREE-LINE SUMMARY:
Win (round 1): bot's own missile-swarm fusion did the work twice — tagging then finishing 3P Ryoma near a waterhole — for a cheap win (23% health lost, only 1 of 9 stones dropped).
Loss (round 2): a long round where the bot's two transforms weren't enough; it dies grappled point-blank inside 4P Accel's own transformed dragon form for the full two seconds before the KO, losing half its stones (5/10).
Vs leg91 / training change: stone retention in a win round finally looks better, but backing off an opponent's transform and playing safer at low health still aren't visible in either filmed round this leg.
