# Scouting report — league leg 63 (Desert Area)

**1. LOSS (ep01, 0:00–1:02)**
Intro 0:00, ACTION 0:04. Bot (2P yellow) starts alone at the map's left edge while Ryoma+Accel cluster at the top-right rocks; it closes in fast and tags Pride "ENEMY" by 0:01, engaging Pride first rather than avoiding. A 4-way scrum forms near the cacti from ~0:12 on, with chests/stones grabbed and thrown almost continuously (0:11, 0:22, 0:28, 0:37–0:45) and a blue/gem stone visible 0:18–0:19. forms=0/1: no bot transform, one opponent transform (unidentifiable in stills). Unlike leg62, all four health bars stay visibly full/undamaged through the last sample at 1:02 (dmg totals are small: +1.40/-1.00) — the round simply cuts to the next intro at 1:03 with no bar dip at all, so this loss's KO isn't just "just past the last frame" (leg61/62's pattern), it's fully invisible at 1 fps — possibly an instant/environmental death rather than a health-drain KO.

**2. WIN (ep06, 7:00–8:56, clip starts mid-round)**
Window opens already in a rock/cactus scrum, all four clustered, chests/stones flying constantly (7:00–7:47) — stones picked=7 vs lost=2, a clean net positive unlike the loss. Accel (4P green) is X'd by 8:31, just after a bright beam/energy effect sweeps the screen at 8:30 with the bot tagged nearby — plausibly the bot's kill but not certain. The bot shows a wing-shaped transform-like effect ~8:53–8:55 (matching forms=2/2). Pride (1P red) isn't X'd until the very last sampled frame, 8:56, amid a chaotic gunfire/explosion pile with the bot tagged "HELP" adjacent — again plausible but unconfirmed. Ryoma (3P blue) still has a full bar when the clip/video ends at 8:56 — the actual final KO happens off-camera past the last sample, same blind spot as leg62's win.

**3. PATTERNS**
- Round-opening isolation at a map edge repeats for a third leg running (leg61, leg62, now leg63), though this time the bot closes the gap almost immediately (~1s) instead of lingering ~8s.
- Loss ep: net stone loss (picked=4, lost=5) vs win ep's net gain (7 vs 2) — matches the outcome directionally.
- Neither KO in the win episode has a confidently-attributed attacker, and the third (Ryoma) is entirely off-camera — same "most kills unattributable" issue as leg62.
- Not visible at 1 fps: the loss's actual KO moment (no visible damage at all beforehand), exact transform trigger times, and attacker credit for 2 of 3 win-episode KOs.

**4. SUGGESTION / TO VERIFY**
Compared to leg62: the edge-isolation opening persists but the bot now recovers from it quickly, and the "can't attribute the finishing KO" problem persists unchanged across both episodes and both legs.
Suggestion: since closing the gap fast (this leg) didn't prevent the loss, the fix is probably elsewhere — investigate what happens in the final 1–2s of loss rounds specifically.
Verify: pull per-tick health/attacker logs for ep01 0:55–1:03 to confirm whether the bot's death is a real gradual-damage KO (invisible at 1 fps) or an instant/environmental kill, since stills show zero bar depletion right up to the round cut.
