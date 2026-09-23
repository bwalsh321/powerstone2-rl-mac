# Scouting report — league leg 70 (Desert Area)

**1. LOSS (ep01, round 1 of 11, 0:00–1:19)**
Bot opens solo by the cactus rise and engages Pride almost immediately (contact ~0:02, before ACTION! at 0:04) — fast engage again. All 3 opponents converge on a chest-heavy patch by 0:08-0:13. Stones: picked=9/lost=3, forms=2/2 — unlike most reviewed losses, the bot actually closes both transforms this round. A large missile/plane swarm fills the screen ~0:44-48 near a green/ENEMY tag with no golden 2P model visible, so per the fusion-swarm rule that reads as Accel's own special, not bot's (echoes leg69's near-identical mislabeling risk). Pride (1P) is dead by ~0:48, well before the round ends. In the last-12s strip the bot (2P) is caught in a multi-enemy flurry ~rel 9.75-10.75s (both red and blue tags visible around it) and its bar X's out at rel ~11.0s (~0:78) — a double-team finish, not one clean attacker; exact credit not resolvable at 4fps.

**2. WIN (ep11, round 11 of 11, 16:20–18:10 video time)**
Opens into the same chest-heavy scrum pattern as the loss. Accel (4P) dies first, ~17:27 (~63s in); Pride (1P) follows, dead by ~17:36 (~72s) — attacker unclear for both at 1fps, multiple fighters overlapping each time. Stones dominate: picked=10/lost=2, forms=3/3, dmg +6.00/-0.98 — every transform attempt closes, unlike the loss's 2/2. The decisive transform lands right at the end: last-12s strip shows the bot's model go golden ~rel 8-10s (video ~18:00-18:02), then fire the screen-filling silver missile/plane swarm at rel ~10.75s — 2P is visibly transformed here, so per rubric this is Falcon's own fusion special. Ryoma (3P), the last opponent standing, dies inside it at rel ~11.0-11.25s (~18:09), sealing the win.

**3. PATTERNS**
- forms=2/2 (loss) vs forms=3/3 (win) — a much smaller transform-closing gap than leg69's 0/1-vs-3/4, worth tracking as a possible improvement rather than one-off variance.
- Same double-team death as leg69's loss: bot swarmed by 2+ enemies in the final seconds with no single clean attacker visible.
- Idle/edge-hugging/wasted-transform: not visible at 1fps either round this leg.

**4. SUGGESTION / TO VERIFY**
Vs leg69: the "transform-closing weaker in losses" pattern flagged there does NOT repeat here (2/2 in this loss vs leg69's 0/1).
Suggestion: both leg69 and leg70's losses end in a multi-enemy dogpile with no disengage — check whether the bot has any retreat behavior when 2+ enemies are adjacent.
Verify: confirm via attacker/combat-log data (not just the 1fps frames) whether the ~0:44-48s swarm in the loss round is logged as Accel's special, to validate the fusion-swarm attribution call above.
