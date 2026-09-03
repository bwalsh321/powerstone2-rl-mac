"""watch_play.py — spectate the model playing, in a real window.

The env drives the game exactly as in eval_parity (same obs, same
deterministic-or-not policy), but every emulated frame is blitted to a
pygame window and paced to real time — so you can SEE what the bot sees
and screen-record it for posterity/reddit.

Keys:  ESC / close window = quit    SPACE = pause    F = fast (no pacing)

Sound: ON by default via `sounddevice` (pip install sounddevice) — the
harness captures the core's audio per frame (emu.get_audio()) but has no
playback path of its own, so we stream it here. SDL_AUDIODRIVER=dummy
does NOT affect this (sounddevice bypasses SDL); keep the usual command.
If sounddevice is missing the script warns once and runs silent.
--no-sound disables; fast-forward mutes automatically.

Usage (linux_port/, venv active):
    SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. python -u watch_play.py \
        --core "$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" \
        --game "../Power Stone 2 (USA).chd" --slot 2
Options: --model <zip> (default legG warm-start copy)  --episodes N
         --stochastic (sample actions)  --scale 2  --speed 1.0
"""
import argparse
import os

import numpy as np
import pygame

from stable_baselines3 import PPO

from powerstone_env_libretro import PowerStoneEnvLibretro


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--model", default="./powerstone_v6_ppo.zip")
    ap.add_argument("--states", default="./states")
    ap.add_argument("--slot", type=int, default=2)
    ap.add_argument("--episodes", type=int, default=0, help="0 = until quit")
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--speed", type=float, default=1.0,
                    help="pacing multiplier; 0 = uncapped")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--record", metavar="OUT.mp4", default=None,
                    help="also encode straight to a video file (frame-exact "
                         "60fps + game audio; works in fast mode too)")
    args = ap.parse_args()

    env = PowerStoneEnvLibretro(
        core_path=args.core, game_path=args.game, states_dir=args.states,
        state_slots=[args.slot])
    model = PPO.load(args.model.removesuffix(".zip"), device="cpu")

    br = env._lr_bridge
    emu = br.emu
    h, w = emu.get_shape()
    pygame.init()
    screen = pygame.display.set_mode((w * args.scale, h * args.scale))
    pygame.display.set_caption("Power Stone 2 — legG spectator")
    clock = pygame.time.Clock()
    buf = np.zeros((h, w, 3), np.uint8)
    state = {"quit": False, "paused": False, "fast": args.speed == 0}

    # ---- audio: stream emu.get_audio() through sounddevice --------------
    audio_stream, audio_ring = None, None
    if not args.no_sound and args.speed == 1.0:
        try:
            import threading
            import sounddevice as sd
            rate = int(emu.get_audio_rate() or 44100)
            lock = threading.Lock()
            ring = np.zeros((0, 2), np.int16)

            def _cb(outdata, frames, t, status):
                nonlocal ring
                with lock:
                    n = min(frames, len(ring))
                    outdata[:n] = ring[:n]
                    ring = ring[n:]
                if n < frames:
                    outdata[n:] = 0          # underrun -> brief silence

            audio_stream = sd.OutputStream(
                samplerate=rate, channels=2, dtype="int16", callback=_cb)
            audio_stream.start()

            def push_audio(s):
                nonlocal ring
                if len(s) == 0 or state["fast"]:
                    return
                with lock:
                    # cap latency at ~6 frames of buffered audio
                    if len(ring) < rate // 10:
                        ring = np.concatenate([ring, s])
            audio_ring = push_audio
            print(f"[watch] sound on ({rate} Hz)")
        except Exception as e:
            print(f"[watch] sound unavailable ({e}) — running silent; "
                  f"pip install sounddevice to enable")
    elif not args.no_sound:
        print("[watch] sound needs --speed 1.0; running silent")

    # ---- recorder: pipe raw frames to ffmpeg, mux audio at the end ------
    rec = None
    if args.record:
        import shutil
        import subprocess
        ff = shutil.which("ffmpeg")
        if not ff:
            try:
                import imageio_ffmpeg
                ff = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ff = None
        if not ff:
            raise SystemExit("[watch] --record needs ffmpeg: "
                             "`pip install imageio-ffmpeg` (easiest) "
                             "or `brew install ffmpeg`")
        vid_tmp = args.record + ".video.mp4"
        proc = subprocess.Popen(
            [ff, "-y", "-loglevel", "error",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
             "-r", "60", "-i", "-", "-an",
             "-vf", "scale=iw*2:ih*2:flags=neighbor",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-pix_fmt", "yuv420p", vid_tmp],
            stdin=subprocess.PIPE)
        rec = {"ff": ff, "proc": proc, "vid": vid_tmp,
               "rate": int(emu.get_audio_rate() or 44100), "audio": []}
        print(f"[watch] recording -> {args.record}  "
              f"(tip: press F to render faster than real time)")

    def pump_events():
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                state["quit"] = True
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    state["quit"] = True
                elif ev.key == pygame.K_SPACE:
                    state["paused"] = not state["paused"]
                elif ev.key == pygame.K_f:
                    state["fast"] = not state["fast"]

    def render_one():
        emu.get_frame(buf, w, h)
        # GL reads frames bottom-up -> flip vertically for display
        surf = pygame.surfarray.make_surface(
            np.transpose(buf[::-1], (1, 0, 2)))
        if args.scale != 1:
            surf = pygame.transform.scale(
                surf, (w * args.scale, h * args.scale))
        screen.blit(surf, (0, 0))
        pygame.display.flip()
        if not state["fast"]:
            clock.tick(60 * args.speed)

    # Render every emulated frame: wrap the bridge's run_frames so ALL
    # paths (actions, intro pumps, stale-read pumps) draw and pace.
    orig_run_frames = br.run_frames

    def run_frames_rendered(n):
        for _ in range(n):
            pump_events()
            if state["quit"]:
                raise KeyboardInterrupt
            while state["paused"]:
                pump_events()
                if state["quit"]:
                    raise KeyboardInterrupt
                clock.tick(30)
            orig_run_frames(1)
            if rec is not None or audio_ring is not None:
                s = emu.get_audio()
                if rec is not None:
                    emu.get_frame(buf, w, h)
                    rec["proc"].stdin.write(buf[::-1].tobytes())
                    rec["audio"].append(s.copy())
                if audio_ring is not None:
                    audio_ring(s)
            render_one()

    br.run_frames = run_frames_rendered

    wins = losses = ep = 0
    try:
        while args.episodes == 0 or ep < args.episodes:
            obs = env.reset()
            done, info = False, {}
            while not done:
                action, _ = model.predict(
                    obs, deterministic=not args.stochastic)
                obs, r, done, info = env.step(action)
            ep += 1
            res = info.get("result", "timeout")
            wins += res == "win"
            losses += res == "loss"
            pygame.display.set_caption(
                f"Power Stone 2 — legG spectator  |  ep {ep}: {res}  "
                f"({wins}W/{losses}L)")
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\nwatched {ep} episodes: {wins}W/{losses}L")
        if audio_stream is not None:
            try:
                audio_stream.stop(); audio_stream.close()
            except Exception:
                pass
        if rec is not None:
            try:
                import os as _os
                import subprocess
                import wave
                rec["proc"].stdin.close()
                rec["proc"].wait()
                wav_tmp = args.record + ".audio.wav"
                allsamp = (np.concatenate(rec["audio"])
                           if rec["audio"] else np.zeros((1, 2), np.int16))
                with wave.open(wav_tmp, "wb") as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(rec["rate"])
                    wf.writeframes(allsamp.tobytes())
                subprocess.run(
                    [rec["ff"], "-y", "-loglevel", "error",
                     "-i", rec["vid"], "-i", wav_tmp,
                     "-c:v", "copy", "-c:a", "aac", "-shortest",
                     args.record], check=True)
                _os.unlink(rec["vid"])
                _os.unlink(wav_tmp)
                print(f"[watch] saved {args.record}")
            except Exception as e:
                print(f"[watch] mux failed ({e}) — raw video kept at "
                      f"{rec['vid']}")
        pygame.quit()
        env.close()


if __name__ == "__main__":
    main()
