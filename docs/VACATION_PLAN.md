# Vacation plan: Oct 14-19 2026 (Blake away; Claude decides)

Blake (Oct 14, 9 pm): full rein for the next 4-5 days of legs. Rules:
- Don't delete anything beyond what is already routine: archiving partial train logs, the battery's normal pool handling.
- A change gets a few legs (a 3-leg read) before anything else changes.
- Keep posting short per-leg notes in the chat; Claude makes the decisions.
- Worst case: the bot gets worse and we restart from a good leg. Every leg's zip is kept
  (powerstone_v6_leg<N>_league.zip + pool_league/prog_leg<N>.zip).

## Where it stands (leg 179)

| | Sampled lv8mix |
|---|---|
| Legs 171-178 (lr 5e-5, frame stack 2 from 174) | about 60 |
| Leg 179 (first 512-wide leg) | 64.4, best ever |

Top-move grades are now 61-73.

Safe restart points:
- leg 179: 512 wide, best.
- leg 178: 256 wide.
- leg 173: 7 frames.

## Plan (one change at a time, 3-leg reads on SAMPLED lv8mix)
1. **Legs 179-181: read the 512-wide network.** Keep it if the average is at least about 60 (legs 171-178).
2. **Ride** while the grade keeps improving. "Flat" = 3-4 legs without a new 3-leg high.
3. **When flat: learning rate 5e-5 -> 2.5e-5** (league_optim.txt; standard step-down; the last cut gave +7). Read 3 legs.
4. **Then, if flat again and time remains: LSTM 128 -> 256** (built and tested: `lstm256` surgery + PS2_LSTM_HIDDEN=256;
   function-preserving; legs ~75% longer, ~7 h). Read 3 legs.
5. Hunters stay at 50%. The hunted grade is flat at ~15-20; not worth a change slot now.

## Revert rules
- A change whose 3-leg sampled average is more than 3 points below the 3 legs before it: revert to the last leg
  before the change. Set league_state.txt to that zip and undo the recipe line. Back up the recipe first.
- Hold gate fires (sampled > 6 below the mean of the last 5):
  - One-off with top-move fine: release.
  - Two holds in a row: revert to the last good leg.
- A leg crashes or the box reboots: relay_boot.sh restarts it; Claude checks wrapper_league.log and relaunches by the
  documented procedure (docs/SESSION_HANDOFF_RYZEN.md section 4) if needed.

## Mechanics
- Only recipe files change (league_optim.txt, league_env.txt, league_surgery.txt, league_state.txt), edited between
  legs or via atomic mv, with a backup in claude_bridge/ each time.
- Everything is logged in docs/NEXT_CHANGES.md and committed.
- No pushes: the box has no GitHub login. Blake pushes from the Mac when back.
- Reports depend on this chat session staying open (background waits). If it dies, the relay keeps training; reports
  resume when a session picks this up again.
- Disk: 275 GB free, ~2.5 GB/day: fine.

## Revised Oct 17 (audit, Blake agreed): order after the current ride
1. Opponent pool recent-only: move pool snapshots older than ~leg 170 to pool_league_archive/ (no deletes).
2. lr 2.5e-5 -> 1.25e-5 at the following plateau.
3. Entropy 0.01 -> 0.005 (needs the PS2_ENT_COEF pass-through merged; agent building it on branch sealed-ent).
4. Second sealed test set (agent, same branch); graded rarely.
5. LSTM 256 last.
