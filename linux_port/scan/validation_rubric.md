# RAM-overlay validation rubric (better eyes, Sep 23 2026)

Each sheet is 6 columns x 8 rows of frames, read left-right then top-bottom, one frame every 15 game
frames (4 per second). Every tile has a black overlay at the top printed FROM EMULATOR RAM at that
exact frame. It is NOT derived from the image. Your job is to check whether the printed values match
what is visible in the picture. Be strict. Do not give the benefit of the doubt. Say "unclear" when the
character is off-screen, tiny, or hidden by effects.

Overlay lines: `f<frame> t=<seconds> P2mask=<bot input>` then one line per player:
`1P-red` = Pride (red HUD, 1P), `2P-yel` = Falcon, THE BOT (yellow, 2P), `3P-blu` = Ryoma (blue, 3P),
`4P-grn` = Accel (green, 4P). Per player: hp (1000 = full; refilled to 1000 every 5 s, ignore refills),
state=<number>:<name>, stun=<frames remaining, counts down over ~0.7 s>, form=1 when transformed.
Last line `fast objs`: pool objects moving faster than 700 units/s, excluding stones/chests/items
(distance to the bot and speed) — expected to be projectiles, thrown objects or special-attack objects.

Check, per tile, for every player you can see:
1. state 32 HIT / 34 HITair with stun>0: is that character visibly reacting to a hit (flinch, knocked
   back, launched, tumbling, lying on the ground, getting up)? Late in the countdown the reaction may be
   ending. Also note a HIT with NO visible hit reaction.
2. state 7 attack: visibly in an attack pose (punch, kick, throw, grab, swing)?
3. state 5 air: visibly off the ground?
4. state 25 XFORM / 26 SPECIAL (form=1): visibly transformed (different model, glow) and/or a special
   attack effect on screen (rockets, beam, burst, swarm)?
5. state 0 idle / 1 walk: standing or walking, NOT attacking and NOT being hit?
6. fast objs listed: is a projectile, thrown object or special effect visible in flight? "none": is the
   screen free of projectiles (thrown cacti, rockets, beams)?
7. hp dropping between consecutive tiles (not a refill): does that player look hit in between?

OUTPUT (<= 45 lines): a table with columns signal | tiles checked | agree | disagree | unclear for the
seven checks, then EVERY disagreement as one line: frame id, player, printed value, what you actually
see. Then two lines: the single most reliable signal and the single least reliable one. No speculation
about code or training.
