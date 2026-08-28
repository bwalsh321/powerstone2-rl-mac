"""bench_fps.py — how fast does the libretro loop actually run on this box?

Measures three layers, worst-in-last order, all on one emulator instance:

  A. raw core      — emu.run() alone (synth detached): the emulation ceiling.
  B. core + synth  — run_frames() with the RAM synth ticking: the transport
                     layer's real per-frame cost (pool sweep every 3rd frame).
  C. full env.step — reset + N random-action steps through PowerStoneEnvV6's
                     obs/reward path: what training actually pays per step.

No model load (PPO predict adds ~1ms/step on top; measure separately if you
care). Numbers print as fps, multiples of real time (60fps), and projected
steps/sec — the server-sizing number.

Usage (linux_port/, venv active):
    SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. python -u bench_fps.py \
        --core <core> --game "../Power Stone 2 (USA).chd" --slot 2
"""
import argparse
import time

from powerstone_env_libretro import PowerStoneEnvLibretro

RAW_FRAMES = 1800      # 30s of game time per timed block
STEP_COUNT = 300


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--states", default="./states")
    ap.add_argument("--slot", type=int, default=2)
    args = ap.parse_args()

    env = PowerStoneEnvLibretro(
        core_path=args.core, game_path=args.game, states_dir=args.states,
        state_slots=[args.slot])
    br = env._lr_bridge
    br.execute(f"loadstate {args.slot}")   # bench mid-match, not boot screens

    # --- A: raw core, synth detached ------------------------------------
    saved = br._synths
    br._synths = []
    t0 = time.perf_counter()
    br.run_frames(RAW_FRAMES)
    dt_a = time.perf_counter() - t0
    br._synths = saved
    fps_a = RAW_FRAMES / dt_a

    # --- B: core + synth tick -------------------------------------------
    t0 = time.perf_counter()
    br.run_frames(RAW_FRAMES)
    dt_b = time.perf_counter() - t0
    fps_b = RAW_FRAMES / dt_b

    # --- C: full env.step loop ------------------------------------------
    obs = env.reset()
    # warm-up (first steps pay caches/JIT)
    for _ in range(10):
        obs, r, done, info = env.step(env.action_space.sample())
    n_frames0 = env._lr_synth.frame
    t0 = time.perf_counter()
    steps = 0
    for _ in range(STEP_COUNT):
        obs, r, done, info = env.step(env.action_space.sample())
        steps += 1
        if done:
            obs = env.reset()      # includes loadstate + intro pump
    dt_c = time.perf_counter() - t0
    frames_c = env._lr_synth.frame - n_frames0
    sps = steps / dt_c
    fps_c = frames_c / dt_c

    print("\n================ BENCH ================")
    print(f"A raw core        : {fps_a:7.1f} fps   ({fps_a/60:4.1f}x real time)")
    print(f"B core + synth    : {fps_b:7.1f} fps   ({fps_b/60:4.1f}x real time)"
          f"   synth cost {100*(dt_b-dt_a)/dt_a:+.1f}%")
    print(f"C full env.step   : {sps:7.1f} steps/s ({fps_c:6.1f} fps incl. "
          f"resets, {fps_c/60:4.1f}x real time, {frames_c/steps:.1f} frames/step)")
    print(f"projected ep len ~1200 steps -> {1200/sps/60:.1f} min/ep single "
          f"instance, model overhead excluded")
    env.close()


if __name__ == "__main__":
    main()
