# M4 MacBook bring-up (Sep 12, 2026 — free move off the M2)

The league relay is PAUSED after leg 20 (lv8 record: 5W/45L). Nothing is
running anywhere. `league_state.txt` reads `21 ./powerstone_v6_leg20_league.zip`
so leg 21 is the first leg this machine trains. Same platform (arm64 macOS),
so the built harness, the core, and the savestates all carry over as-is —
no rebuilds, no Linux gates.

## 1. On the M4

1. Download the zip from Google Drive, unzip somewhere permanent, e.g.
   `~/Documents/macbook_migration` (keeping the same folder name keeps every
   doc and habit true).
2. Install Homebrew if it is not there (https://brew.sh), then:

```bash
cd ~/Documents/macbook_migration
bash setup_m4.sh          # python 3.11 + tmux, ~/ps2rl venv, core install, G1-G2
```

## 2. Parity gate (G3) — quick, do not skip

Same-architecture move, so this should sail, but the chest-obs law says
verify anyway (~40 min):

```bash
cd ~/Documents/macbook_migration/linux_port
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
python eval_parity.py \
  --core "$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" \
  --game "../Power Stone 2 (USA).chd" --slot 2 --episodes 50 \
  --model ./powerstone_v6_leg20_league.zip
# M2 reference (Sep 11): win% 88.0, picks 10.56, forms 3.22 — expect within a
# few points and a PARITY PASS line.
```

## 3. Reconnect Claude and resume the league

1. Install the Claude desktop app on the M4, open the existing task/session,
   and choose "Link to this computer". Connect the
   `~/Documents/macbook_migration` folder.
2. Start the command bridge:

```bash
cd ~/Documents/macbook_migration/linux_port && tmux new -s claudebridge -d "caffeinate -is bash claude_bridge_watcher.sh"
```

3. Tell Claude the M4 is up — it verifies the bridge and launches leg 21
   (and applies the 2M -> 4M leg-length change then, if approved). Manual
   fallback: `tmux new -s ps2train -d "caffeinate -is bash league_leg.sh"`
   from `linux_port/`.

### Bring-up findings on the actual M4 (Sep 11, first session)

Three things the "carries over as-is" assumption missed; all now handled by
`setup_m4.sh` step 3b, listed here so nobody re-debugs them:

1. **Gatekeeper quarantine.** Everything unzipped from a browser download
   carries `com.apple.quarantine`, and macOS refuses to dlopen the M2-signed
   `sdlarch-rl/_retro.so` ("code signature not valid for use in process:
   library load disallowed by system policy"). Fix: `xattr -dr
   com.apple.quarantine <folder>` then `codesign -s - -f` on `_retro.so`,
   `libpcsx2_headless.dylib` and both copies of the flycast core.
2. **Baked rpath.** `_retro.so` looks for `libpcsx2_headless.dylib` under
   `/Users/blakewalsh/Documents/macbook_migration/sdlarch-rl/build/Release`
   (the M2's username/path). Fix: `install_name_tool -add_rpath
   <checkout>/sdlarch-rl sdlarch-rl/_retro.so` (the dylib is already there),
   then re-sign.
3. **SDL2.** `_retro.so` links `/opt/homebrew/opt/sdl2-compat/lib/
   libSDL2-2.0.0.dylib`; `brew install sdl2-compat`.

Also: the folder landed in `~/Downloads/macbook_migration` on this machine;
a symlink `~/Documents/macbook_migration -> ~/Downloads/macbook_migration`
keeps every documented path true. This Mac is on US/Pacific time (the M2
logged EDT); `wrapper_league.log` timestamps before Sep 11 18:00 are EDT.
`defaults write org.python.python ApplePersistenceIgnoreState YES` applied
(HANDOFF: do this on any new Mac). `system/dolphin-6` and `dolphin-7`
seeded for an 8-worker probe. The Claude session on this machine runs a
shell directly on the Mac (no VM), so the file bridge is optional here.

## What moved / what did not

IN: all linux_port scripts + receipts + train logs, states/, pool_league/,
demos + demos_lv8 + demos_v4corpus + demos_cheater, all model zips
(powerstone_v6_ppo.zip = the never-overwrite champion), league_state.txt,
the CHD, the flycast core (cores/), HANDOFF.md + SESSION_HANDOFF.md +
reddit docs, requirements.txt, sdlarch-rl (source + built harness, .git
stripped — re-clone from bwalsh321/sdlarch-rl if you want history).
OUT: checkpoints_* dirs (historical only), both repos' .git (run
`git clone https://github.com/bwalsh321/powerstone2-rl-mac.git` fresh or
re-init if you want repo ops on the M4), the ~/ps2rl venv (rebuilt by
setup), claude_bridge scratch.

Fresh-machine bonuses: the Metal boot race should vanish (it was an uptime
disease — PS2_STAGGER can drop back to 20), and watch whether the teardown
hang follows; if it does, the os._exit(0) patch is still on the table.
