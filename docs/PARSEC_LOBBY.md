# Side project: "Beat the bot" lobby over Parsec (idea, Oct 13 2026)

**Idea (Blake):** people watch odd games on TikTok/YouTube. Host the bot on a spare box, let people remote in with
Parsec and play against it in four-player free-for-alls, and stream the matches.

## Hardware
- Lenovo M715q, Ryzen 5 PRO 2400GE (4 cores / 8 threads, Vega 11 graphics). That is enough for one flycast emulator,
  the bot's policy (small, runs on the CPU) and Parsec's hardware video encoding. No extra GPU is needed to start.
- Windows host: Parsec hosts only on Windows/macOS, not Linux. Wired ethernet.
- No training on this box: copy the current best bot zip over now and then.

## What exists already
- `linux_port/play_vs.py` (Sep 16): one human with a gamepad vs the bot live.
  - Modes: 1v1, ffa (bot copies in the other seats), mixed (CPU in a seat).
  - `--opps pool` samples past bots.
  - Logs results from the bot's side.
- Parsec guests appear on the host as ordinary virtual Xbox controllers, which pygame sees as joysticks.

## Steps
1. **Multi-pad `play_vs.py`:** up to 3 controllers mapped to P1/P3/P4. Seats with no controller are filled by the lv8
   CPU or a pool bot.
2. **Fresh-round start:** savestates at round start with chosen characters, instead of the training states' random
   mid-match pre-roll. `menu_drive.py` / `make_savestates.py` can stamp them.
3. **Windows setup on the M715q:** flycast core, Python venv, the harness built for Windows (the project started on
   Windows: github.com/bwalsh321/powerstone2-rl).
4. **Local test:** Blake with 2 pads on the box. Then a Parsec guest test (feel the lag).
5. **Stream:** OBS on the host to YouTube/Twitch, with an overlay (win rate vs humans, bot leg number).
6. **Log every human match** (results plus per-round stats) as a "vs humans" test set. Human games are too few to
   train on directly (one leg ≈ 100+ hours of play; imitation (DAgger) cost 6-15 points), but they show where the
   bot really loses.

## Notes
- Power Stone 2 is Capcom's game: hobby streaming is generally tolerated (let's-plays); don't monetize; never share
  the game dump.
- Spare GPUs/parts are available if the 2400GE falls short; not expected.
