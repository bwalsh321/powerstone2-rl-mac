"""diag_state.py — what does a stamped savestate actually do over time?

Loads a slot state, pumps frames headless, and reports the health quad +
match-readiness once a second (60 frames). Three phases:

  phase A (0-30s):   hands off. Detects states that auto-advance to the
                     fight (round intro / READY-FIGHT stamps).
  phase B (30-45s):  taps DC A once a second. Detects menu screens that
                     need a confirm.
  phase C (45-60s):  taps Start once a second. Detects pause / press-start
                     screens.

Exit prints the first frame (and phase) where match-ready went true, or a
verdict that the state never reaches a fight without real navigation.

Usage (linux_port/, venv active):
    SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. python -u diag_state.py \
        --core <core> --game "../Power Stone 2 (USA).chd" --state 2
"""
import argparse

from flycast_bridge import FlycastBridge
from ps2_ram import StateLineSynth

AGENT_IDX = 1          # in-game P2, same as PowerStoneEnvV6.AGENT_PLAYER - 1
DC_A, DC_START = 0x004, 0x008


def parse_h(line):
    v = line.strip().split(",")
    try:
        return [float(x) for x in v[1:5]]
    except (ValueError, IndexError):
        return [0.0, 0.0, 0.0, 0.0]


def ready(h):
    me = h[AGENT_IDX]
    opps = [x for j, x in enumerate(h) if j != AGENT_IDX]
    return me > 100.0 and any(x > 100.0 for x in opps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--states", default="./states")
    ap.add_argument("--state", type=int, default=2)
    args = ap.parse_args()

    br = FlycastBridge(args.core, args.game, args.states)
    synth = StateLineSynth(br.ram, bot_player=2)
    br.attach_synth(synth)
    br.run_frames(4)
    br.execute(f"loadstate {args.state}")

    first_ready = None
    for sec in range(60):
        if sec == 30:
            print("--- phase B: tapping DC A once/sec ---")
        if sec == 45:
            print("--- phase C: tapping Start once/sec ---")
        if 30 <= sec < 45:
            br.execute(f"press {DC_A} 6")
            br.execute("press 0 6")          # release
            br.run_frames(48)
        elif sec >= 45:
            br.execute(f"press {DC_START} 6")
            br.execute("press 0 6")
            br.run_frames(48)
        else:
            br.run_frames(60)
        h = parse_h(synth.line)
        r = ready(h)
        if r and first_ready is None:
            first_ready = synth.frame
            phase = "A (hands-off)" if sec < 30 else (
                "B (needed A press)" if sec < 45 else "C (needed Start)")
            print(f"*** MATCH READY at frame {synth.frame}, phase {phase} ***")
        print(f"t={sec+1:2d}s frame={synth.frame:5d} "
              f"h=[{h[0]:7.1f},{h[1]:7.1f},{h[2]:7.1f},{h[3]:7.1f}] "
              f"ready={r}")

    if first_ready is None:
        print("VERDICT: never match-ready in 60s even with A/Start taps —")
        print("the stamp is not at (or near) round start. Re-stamp slot2")
        print("closer to the READY/FIGHT moment (healths visible on screen).")
    else:
        print(f"VERDICT: reaches fight (first ready at frame {first_ready}).")
    br.close()


if __name__ == "__main__":
    main()
