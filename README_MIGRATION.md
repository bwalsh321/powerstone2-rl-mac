# MacBook migration kit (Aug 23)

Copy this whole folder to the M2, then follow `linux_port/MAC_TEST.md`.
Everything below is about where each piece GOES on the Mac — the
MAC_TEST doc takes over from there.

## What's in here

- `linux_port/` — the entire port harness + both docs (README_PORT.md
  is the truth, MAC_TEST.md is the macOS setup in front of it). Keep
  the folder together; the scripts import each other by relative path.
- `Power Stone 2 (USA).chd` — 260 MB, md5 `72aa612c...014f8`, verified
  identical to the rig's master copy. MAC_TEST step 4 expects it one
  level ABOVE linux_port (`../Power Stone 2 (USA).chd`), i.e. exactly
  the layout of this folder — so you can run gates straight from here.
- `powerstone_v6_ppo_legG_27911k.zip` — the gate-4 parity model
  (known per-slot Windows band to compare against).
- `powerstone_v6_ppo_legM_final.zip` — the reigning champ, for
  eyeballing once parity passes. (If Leg P dethroned M overnight,
  grab `powerstone_v6_256_ppo_legP_final.zip` off the rig too —
  checkpoints are portable, the arch travels inside the zip.)

## BIOS: correction to MAC_TEST step 1

MAC_TEST.md says to copy the Dreamcast BIOS from
`flycast-win64-2.6/data/`. **Those files do not exist on this rig** —
no `dc_boot.bin` / `dc_flash.bin` anywhere. The Windows Flycast has
been running the game on its built-in HLE BIOS the entire project.

The libretro flycast core has the same fallback: in RetroArch, set the
core option **"HLE BIOS" = enabled** (Quick Menu -> Options after
loading the core) and skip the `system/dc/` copy entirely. The RetroArch
smoke test in MAC_TEST step 2 is where you confirm this — if the CHD
boots there with HLE on, the BIOS question is closed for the whole
port. Only if the core refuses would real BIOS files need sourcing,
and they'd be new to the project, not copied from the rig.

## Not in here, on purpose

- Savestates (`.state`) — standalone-Flycast states don't load in the
  libretro core; gate 2 re-records them fresh on the Mac.
- sdlarch-rl — cloned and built ON the Mac (MAC_TEST step 3).
- The flycast core itself — RetroArch's Core Downloader fetches the
  arm64 `flycast_libretro.dylib`.
- The rest of the repo — the port folder is deliberately
  self-contained; nothing else imports into it.
