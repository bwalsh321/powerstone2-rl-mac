# Observation-overlay validation rubric (obs v3 end to end, Sep 23 2026)

Each sheet is 6 columns x 8 rows of frames, left-right then top-bottom, one frame every 3 policy
steps (about 3 per second). The black overlay at the top of each tile is decoded FROM THE BOT'S OWN
OBSERVATION VECTOR at that step, after the whole pipeline (emulator RAM -> state line -> parser ->
observation builder). It is NOT derived from the picture. Check whether it matches what is visible.
Be strict. "unclear" when a character is off-screen, tiny, or hidden by effects.

Overlay lines: `self 2P-yel Falcon` = THE BOT (yellow HUD, 2P). `opp1..opp3` = the three opponents
ordered NEAREST-FIRST from the bot; each line names which player it is (1P-red Pride, 3P-blu Ryoma,
4P-grn Accel). Per line: hp (1.00 = full), stun (frames of hit-stun remaining, counts down over ~0.7 s),
and a state class: idle/walk, AIR (off the ground), ATTACK (attack/throw/grab animation), HIT (hit
reaction, knocked down, getting up), XFORM (transforming), SPECIAL (transformed and using the special),
other, or (none) when the slot is empty (fewer than 3 opponents alive).
Last line: three projectile slots P1..P3, YES with d=(dx,dz) game units from the bot and v=(vx,vz)
units/s when the observation holds a projectile, else "no". Stones, chests and ground items are NOT
projectiles; rockets, beams, bolts, thrown cacti/items are.

Check, per tile, for every named character you can see:
1. HIT with stun>0: visibly reacting to a hit? Also note HIT with no visible reaction.
2. ATTACK: visibly in an attack pose?
3. AIR: visibly off the ground?
4. XFORM / SPECIAL: visibly transformed and/or a special effect on screen?
5. idle/walk: standing or walking, not attacking, not being hit?
6. opp ordering: is opp1 really the nearest opponent to the bot, opp3 the farthest?
7. projectile slots: YES -> a projectile/thrown object/special object visible? "no" on all three -> none
   in flight? A volley (rockets, bolts) should fill several slots.
8. hp: does a printed hp drop between consecutive tiles match a visible hit on that character?

OUTPUT (<= 45 lines): a table signal | tiles checked | agree | disagree | unclear for the eight checks,
then EVERY disagreement as one line: frame id (from the overlay's "step"), which line, printed value,
what you actually see. Then two lines: most reliable signal, least reliable signal. No speculation
about code or training.
