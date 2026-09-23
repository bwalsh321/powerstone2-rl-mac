# Scouting report — league leg 67 (Desert Area)

**1. LOSS (ep01, round 1 of 2, 0:00–~2:00)**
Bot opens alone on the rocky rise by the big cactus (0:00, ACTION! 0:04) and closes into the 3-opponent cluster fast (~3-7s, contact by 0:07) — same quick-close as leg66. Scrum runs across sand/cacti with chests (stones picked=8/lost=3, opp stones down 13(-8), forms=2/3); first fusion swarm ~0:37-41 (tagged 2P, Falcon's own per the rubric). Ryoma (3P) goes down first, ~1:09 (bar X, amid an on-map bomb-prop countdown, unrelated to the swarm). Pride (1P) falls next, ~1:45-47, in a white burst near "ENEMY" — plausible bot credit but not certain at 1fps. A second bot swarm flickers ~1:48-50 in the last-12s strip; the fight then becomes bot vs Accel (4P) alone, and after a bomb-item countdown ("1", explosion ~1:56) the round ends with the bot (2P) X'd at ~1:59 — Accel lands the final hit with no transform effect visible at the kill itself.

**2. WIN (ep02, round 2, ~2:20–5:01)**
Same fast open (ACTION! 2:24, contact ~2:28). Long scrum nets stones picked=12/lost=4, opp down 17(-6), forms=3/4. Bot transforms and throws a robot/plane swarm ~3:36-39 that KOs Ryoma (3P) — bot's own fusion special. Accel (4P) falls next, ~4:44-46, inside a second bot swarm (also bot credit). Pride (1P) is last: the last-12s strip shows a third swarm ~4:57-58 followed by Pride's bar going X right at the final sampled frame, ~5:00 — bot is sole survivor, all 3 KOs plausibly its own.

**3. PATTERNS**
- Fast opens (~3-7s) hold across both rounds, matching leg66, not leg64's slow one.
- HELP tags cluster right before each KO in both rounds (loss 1:08-1:19, 1:59, 2:07-15; win 4:08-21, 4:57) — consistent with the recurring "ganged" pattern, but whose HUD icon (attacker vs. target) isn't resolvable at 1fps.
- Loss round: bot burns 2 of 3 available forms but still loses the final 1v1 to Accel with no swarm visible at its own death — the 0:37 transform landed no confirmed kill, a possible wasted use.
- Win round lands all 3 KOs adjacent to bot swarms (4th leg running, 64-67, of swarm-adjacent finishes) — swarm now reads as the dominant kill mechanism, not just a bonus.

**4. SUGGESTION / TO VERIFY**
Vs leg66: the fast open and "swarm-adjacent kills" streaks both continue; this leg's loss again shows no clean bot-death visual until the very last frame, similar to leg66's ambiguous ending, though here an X does eventually appear.
Suggestion: since the loss round's first transform (~0:37) produced no confirmed KO while a later one preceded the bot's own death, consider whether early-round transforms are spent defensively/reactively rather than held for a clean finish like the win round shows.
Verify: pull the per-tick damage log for loss ep01 0:37-0:50 to confirm whether the bot's own swarm hit any opponent — no HUD damage numbers are legible at 1fps/4fps for that window.
