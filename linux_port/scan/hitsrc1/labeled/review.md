# Hit-source RAM field review (visual check against screenshots)

Rule used to identify seats: the on-screen "ENEMY" tag above a character is colored by that character's HUD seat (P1/Pride=red-pink, P2/Falcon=plain yellow "2P" locator with no ENEMY label since she is the recording POV, P3/Ryoma=blue, P4/Accel=green). Confirmed directly from frames 115/136 (blue-tag Ryoma mid-swing on red-tag Pride, matching RAM+state) and frame 1103 (red-tag Pride's beam hitting green-tag Accel).

| Frame | RAM label | What's visible | Verdict |
|---|---|---|---|
| 115 | P1 hit by P3 DIRECT | Blue-tag Ryoma right next to red-tag Pride, arm/weapon extended into him | AGREE |
| 136 | P1 hit by P3 DIRECT | Ryoma mid sword-swing on Pride, impact sparkle stars between them | AGREE |
| 150 | P1 hit by P3 DIRECT | Ryoma swinging into Pride again, motion-trail swoosh + ring effect at Pride's feet | AGREE |
| 209 | P2 hit by P4 DIRECT | Green-tag Accel's leg extended in a kick right at crouched/staggering Falcon | AGREE |
| 230 | P2 hit by P4 DIRECT | Accel still adjacent to Falcon (bottom-left corner), active pose continuing the combo | AGREE |
| 253 | P2 hit by P4 DIRECT | Accel mid-kick directly over Falcon, clean contact | AGREE |
| 302 | P2 hit by P4 DIRECT | Accel grappling Falcon at point-blank range | AGREE |
| 323 | P2 hit by P4 DIRECT | Accel and Falcon locked together, same combo | AGREE |
| 346 | P2 hit by P4 DIRECT | Accel kicking down onto Falcon, adjacent | AGREE |
| 463 | P2 hit by P4 via OBJECT 0xc50eee4 | Accel adjacent to Falcon holding/swinging a rifle-shaped item into her; no ranged projectile visible, but a handheld item is the contact point | AGREE |
| 465 | P2 hit by P4 via OBJECT 0xc50eee4 | Same object/pose continuing, item at contact point with Accel still adjacent | AGREE |
| 469 | P2 hit by P4 via OBJECT 0xc50ffa4 | New object instance, same adjacent Accel+Falcon contact | AGREE |
| 472 | P3 hit by P1 DIRECT | Red-tag Pride kicking/launching blue-tag Ryoma, white flash + pink gem effect between them | AGREE |
| 473 | P2 hit by P4 via OBJECT 0xc510804 | Accel and Falcon still locked together; a large purple/lavender item visible at the contact point | AGREE |
| 658 | P2 hit by P1 DIRECT | Three-way scrum: Falcon (victim) with Accel grappling from below and Pride's small body tucked directly against her head/face - Pride is in contact | AGREE (scrum, but P1 visibly touching) |
| 676 | P4 hit by P1 DIRECT | Only Falcon and Accel (victim) are visible in contact; Pride's body cannot be distinguished anywhere in the cluster | UNCLEAR |
| 677 | P2 hit by P1 DIRECT | Bright hit-flash obscures the scrum; only Accel is clearly grappling Falcon, Pride not distinguishable | UNCLEAR |
| 864 | P3 hit by P4 DIRECT | Falcon stands directly adjacent to victim Ryoma; Accel's body is not visible anywhere on screen (green tag only marks a large crystal formation that may be occluding him) | UNCLEAR |
| 891 | P3 hit by P4 via OBJECT 0xc50b874 | Accel only appears as a tiny distant silhouette at the far top-right edge; the glowing orb/beam near Ryoma is not clearly identifiable as his projectile | UNCLEAR |
| 892 | P3 hit by P4 via OBJECT 0xc50b874 | Same as 891, continuing - Accel still only a distant speck, no clear projectile link to Ryoma | UNCLEAR |
| 1022 | P4 hit by P2 DIRECT | Victim engulfed in a white/cyan light-pillar effect with red-tag Pride's body at the top of it; Falcon (credited) stands idle several body-lengths below, not visibly touching anything | DISAGREE |
| 1103 | P4 hit by P1 DIRECT | Pride (transformed, mecha-like) firing a beam straight up into airborne Accel just above him | AGREE |
| 1142 | P4 hit by P1 DIRECT | Pride's fiery phoenix/transformed form shooting a fire trail across the screen into Accel, impact sparkles on Accel | AGREE |
| 1161 | P4 hit by P1 DIRECT | Same transformed-Pride fire attack connecting with Accel again | AGREE |

AGREE 18 / DISAGREE 1 / UNCLEAR 5 of 24

Notes on the disagreement/unclear cases:
- Frame 1022 is the one clean DISAGREE: the RAM credits P2 (Falcon), but Falcon is standing idle well away from the victim, while P1 (Pride) is the character actually positioned inside/on the hit-effect column at the victim's location.
- The five UNCLEAR frames (676, 677, 864, 891, 892) all involve the credited attacker (P1 or P4) being invisible, occluded, or reduced to a distant speck, while a different player (Falcon or Accel) is the only one clearly touching the victim - can't rule the RAM label in or out from the pixels alone.
- All 18 AGREEs are frames where the credited player's body (or, for "via OBJECT" hits, an item at the contact point with that player standing right there) is directly adjacent to and touching the victim, consistent with the RAM's DIRECT/OBJECT distinction.
