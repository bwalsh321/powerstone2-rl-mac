# Scouting report — league leg 62 (Desert Area)

**1. LOSS (ep01)**
Intro at 0:00; HUD 0:01. Bot (yellow) sits alone near a cactus at the map edge while Pride/Ryoma cluster together up top; it doesn't close in until ~0:08, joining a scrum at the chests. Stones/gems spawn repeatedly (0:11, 0:19, 0:36) and chests are grabbed/thrown constantly, mostly by Accel (0:12–0:23, 0:33–0:45). Big opponent specials fire off — light-ring bursts 0:17–0:19/0:27, fire explosions 0:24–0:29, a missile swarm 0:42–0:43 — consistent with forms=1/2 (opponents' two transforms; the bot's single one isn't identifiable in stills). Accel (4P, green) is X'd out by ~1:07–1:11 mid-scrum, attacker unclear. The bot's own bar drains to a sliver by 1:10–1:12 while boxed in near cacti with Pride and Ryoma both tagged adjacent ("ENEMY"/"HELP" cluttering the HUD); the round cuts to the next intro at 1:13 with the bar still critical — the literal KO is just past the last sample, same as leg61's loss.

**2. WIN (ep02)**
New intro 1:13, ACTION 1:16, all bars full 1:14. Opens with bot+Pride paired at one edge while Ryoma+Accel start together elsewhere (mirrors the loss's opening split). Chest-carrying/throwing is constant again 1:18–1:23. Accel's bar goes from full to critical between an unseen burst at 1:38–1:39 and is X'd by 2:10 — no clear attacker frame-to-frame. Pride erodes more gradually, is red/blinking by 2:36–2:44, then a red "KO" flash covers the screen at 2:45 with the bot tagged adjacent mid-swing; Pride is X'd by 2:46 — the bot plausibly lands this one. Ryoma stays healthy the longest; the bot shows a golden transform-like glow at 2:24 and again 2:49–2:51 (forms=3/0). The clip ends at 2:55 mid a missile/rocket-swarm effect centered on Ryoma with the bot adjacent — the video stops there, so the finishing KO (and the win) falls just past the last sample, unattributed, echoing leg61's Ryoma death.

**3. PATTERNS**
- Opens isolated at a map edge for ~8s while the other three group up first — same shape as leg61's loss opening; still not visible whether it's deliberate.
- Loss ends boxed in by two opponents at once near terrain, not a clean 1v1 — repeats leg61's corner-trap loss almost exactly.
- Both eps: chests/gems are grabbed and thrown near-continuously by all four fighters; several stones sit unclaimed for 2–4s at a time.
- Win ep: of 3 opponent KOs, only Pride's (2:45–2:46) looks like the bot's own kill; Accel's and Ryoma's both happen off-camera/ambiguous, same ratio as leg61 (1 of 2 clear).
- Not visible at 1 fps: exact attacker credit for 3 of 4 KOs this leg, precise transform trigger timing, or idle/jump-spam behavior between samples.

**4. SUGGESTION / TO VERIFY**
Compared to leg61: essentially the same two failure/success shapes recur (isolated opening → corner-trapped loss; win via one bot-credited kill plus two ambiguous off-camera kills) — this looks like a stage/opponent-mix pattern rather than a one-off.
Suggestion: bias the bot to close the gap toward the other fighters in the first ~8s of a round instead of lingering at the map edge, since that opening isolation shows up in both this leg's loss and leg61's.
Verify: pull per-frame health/attacker logs for both episodes to confirm who actually lands the Accel and Ryoma kills in the win, and whether the loss-episode final hit came from Pride or Ryoma — stills can't attribute 3 of the 4 KOs at 1 fps.
