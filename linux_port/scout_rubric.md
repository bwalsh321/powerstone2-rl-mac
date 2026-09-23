# Fight-scouting rubric (read videos/review_leg<N>/*.png, write videos/review_leg<N>.md, <= 25 lines)
Bot = YELLOW Falcon, "2P" (yellow health bar, second from left). Opponents = level-8 COMs Pride (red 1P),
Ryoma (blue 3P), Accel (green 4P), Desert Area. Sheets are 1 frame/second, 4x3, read left-right then
top-bottom, timestamp top-left. Frames before the HUD appears are intro, not play. episodes.txt lists
the rounds, which sheets belong to the first LOSS and the first WIN, and the per-round stats lines.
Move identification (Blake, Sep 22): when the bot (2P) is transformed, the missile / plane / robot SWARM
that fills the screen is FALCON'S OWN fusion special, fired at close range — credit KOs inside it to the
bot. Other characters have their own transformed specials (beams, fire, ice); do not label every swarm
as an opponent transform.
DATA DICTIONARY (Sep 23, after Astra's review): in the stats lines, forms=A/B means A = number of times the
BOT transformed, B = number of times any OPPONENT transformed. It is NOT closed/attempted; there is no
attempt count. chests=X(Y): X = chests opened anywhere in the arena, Y = chests that vanished near the bot
(proximity heuristic), not chests the bot opened. picked/lost = bot stone pickups / stones knocked off the
bot; opp=P(-L) = opponent pickups / stones opponents lost. dmg +out/-in are health fractions across all
opponents (not the reward). Never report these as rates or success percentages.
Sections: 1. LOSS what happened (opening position, engage vs avoid, stones, transform, how it dies).
2. WIN what happened (same, plus how each KO came about, bot's own or not). 3. PATTERNS the numbers
miss (idle, edge/corner hugging, double-teamed, ignoring nearby stones, wasted transform, same death
twice, not finishing a low opponent) with timestamps; say "not visible at 1 fps" when unsure.
Each episode also has a <tag>_last12s_4fps.png strip: its final 12 s at 4 frames/s (48 tiles, 6 columns x
8 rows, left-right then top-bottom, timestamps relative to the strip start) — use it for the KO moment
and attacker credit; prefer it over the 1 fps sheets for anything in the last seconds.
4. ONE behavioral suggestion and ONE thing to verify by another measurement. No speculation about
code or training. Compare with the previous leg's review file if it exists (one line).
