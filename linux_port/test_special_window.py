"""Sep 27 2026: unit test for the special-damage WINDOW (PS2_SPECIAL_WINDOW) and the lv8 death-cost
override (PS2_LOSS_SCALE_LV8). No emulator: builds the FFA env object without __init__ and drives
_zero_sum_reward with synthetic state lines. Run:
  PS2_OBS_V2=1 PS2_OBS_V3=1 PS2_ZERO_SUM=1 PS2_SPECIAL_DMG_W=1.0 PS2_SPECIAL_R=700 \
  PS2_SPECIAL_WINDOW=2.0 PS2_LOSS_SCALE_LV8=0.5 python test_special_window.py
"""
import os, sys
os.environ.setdefault("PS2_OBS_V2", "1")
from ffa_selfplay_env import FFASelfPlayEnv, SPECIAL_WINDOW, SPECIAL_DMG_W
import ffa_selfplay_env as F

def make_env(window_s, clock="steps"):
    e = FFASelfPlayEnv.__new__(FFASelfPlayEnv)
    e._spec_clock = clock; e._spec_win_frames = int(round(window_s * 60.0)); e._spec_last_frame = {}; e._spec_now_frame = None
    e._pen_step = {}; e._ev = None
    e._present_seats = lambda: [0, 1, 2, 3]
    e._learner_idx = 1
    e._episode_slot = 30                      # lv8 P4 COM slot -> level 8
    e.SLOT_META = F.ffa_slot_meta([30], FFASelfPlayEnv.SLOT_META)
    e._zs_gem = {}; e._zs = {"raw": 0.0, "opp_mean": 0.0, "adj": 0.0, "dealt_nn": 0.0, "n": 0}
    e._spec_win = int(round(window_s * 60.0 / e.ACTION_FRAMES)); e._spec_last = {}; e._spec_t = 0
    return e

def state(pstate, learner_pos=(0, 0, 0), caster_pos=(100, 0, 0), frame=0):
    pos = [(5000, 0, 5000), learner_pos, (-5000, 0, -5000), caster_pos]
    return {"players": [{"pos": p, "gems": 0, "form": 0} for p in pos], "pstate": list(pstate), "frame": frame}

def run(window_s, hit_step, caster_special_steps=(1,), n=40, dmg=0.10, clock="steps", frames_per_step=6):
    """frames_per_step: int, or a function step -> frames advanced by that decision (6 = attack, 10 = movement)."""
    e = make_env(window_s, clock)
    h = [1.0, 1.0, 1.0, 1.0]
    prev = state([0, 0, 0, 0])                # the special is SEEN as a stepped frame (t=1), like the real loop
    frame = 0
    for t in range(1, n):
        frame += frames_per_step(t) if callable(frames_per_step) else frames_per_step
        ps = [0, 0, 0, 26 if t in caster_special_steps else 0]
        s = state(ps, frame=frame)
        nh = list(h)
        if t == hit_step:
            nh[1] = h[1] - dmg
        e._zero_sum_reward(prev, h, s, nh, {})
        prev, h = s, nh
    return e._zs.get("spec_pen", 0.0), e._spec_win

fails = 0
def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: fails += 1

assert SPECIAL_DMG_W > 0, "run with PS2_SPECIAL_DMG_W=1.0"
sp, win = run(0.0, hit_step=11)
check(f"window 0: hit 10 steps after the special -> no penalty (spec_pen={sp:+.3f})", abs(sp) < 1e-9)
sp, win = run(2.0, hit_step=11)
check(f"window 2 s = {win} steps: hit 10 steps (1.0 s) after -> penalty (spec_pen={sp:+.3f})", abs(sp + 0.10 * SPECIAL_DMG_W) < 1e-9)
sp, win = run(2.0, hit_step=21)
check(f"window 2 s: hit exactly {win} steps after -> penalty (spec_pen={sp:+.3f})", abs(sp + 0.10 * SPECIAL_DMG_W) < 1e-9)
sp, win = run(2.0, hit_step=22)
check(f"window 2 s: hit {win + 1} steps (2.1 s) after -> NO penalty (spec_pen={sp:+.3f})", abs(sp) < 1e-9)
sp, win = run(2.0, hit_step=5, caster_special_steps=(5,))
check(f"window 2 s: hit during the special itself -> penalty (spec_pen={sp:+.3f})", abs(sp + 0.10 * SPECIAL_DMG_W) < 1e-9)
sp, win = run(2.0, hit_step=10, caster_special_steps=())
check(f"window 2 s: no special ever -> no penalty (spec_pen={sp:+.3f})", abs(sp) < 1e-9)
# far caster: window must still respect the radius
e = make_env(2.0); h = [1.0] * 4
prev = state([0, 0, 0, 0], caster_pos=(5000, 0, 0))
for t in range(1, 12):
    s = state([0, 0, 0, 26 if t == 1 else 0], caster_pos=(5000, 0, 0)); nh = list(h)
    if t == 10: nh[1] = 0.9
    e._zero_sum_reward(prev, h, s, nh, {}); prev, h = s, nh
check(f"window 2 s: caster 5000 units away -> no penalty (spec_pen={e._zs.get('spec_pen', 0.0):+.3f})", abs(e._zs.get("spec_pen", 0.0)) < 1e-9)
# death cost at lv8
e = make_env(0.0)
lv8 = e.LOSS_SCALE_BY_LEVEL.get(8)
want = float(os.environ.get("PS2_LOSS_SCALE_LV8", "0.2"))
check(f"LOSS_SCALE_BY_LEVEL[8] = {lv8} (env PS2_LOSS_SCALE_LV8={os.environ.get('PS2_LOSS_SCALE_LV8', 'unset')} -> want {want}); death at lv8 costs {e.LOSS_PENALTY * lv8:.1f} vs win +{e.WIN_BONUS:.0f}", abs(lv8 - want) < 1e-9)
check(f"lv3 death scale untouched = {e.LOSS_SCALE_BY_LEVEL.get(3)}", abs(e.LOSS_SCALE_BY_LEVEL.get(3) - 0.7) < 1e-9)
# episode reset clears the tracker
e = make_env(2.0); e._spec_last = {3: 5}; e._spec_t = 7
check("_in_special true inside the window", e._in_special(3, [0, 0, 0, 0]))
e._spec_last = {}; e._spec_t = 0
check("tracker cleared -> _in_special false", not e._in_special(3, [0, 0, 0, 0]))
# ---- Sep 28 (Astra review 3, finding 1): the clock. Movement decisions run 10 frames, not 6.
sp, win = run(2.0, hit_step=21, clock="steps", frames_per_step=10)
check(f"LEGACY clock=steps, movement-only (10 f/step): hit 20 decisions = 200 frames = 3.33 s after -> penalty (documents the bug; spec_pen={sp:+.3f})", abs(sp + 0.10) < 1e-9)
sp, win = run(2.0, hit_step=21, clock="frames", frames_per_step=10)
check(f"clock=frames, movement-only: hit 200 frames (3.33 s) after -> NO penalty (spec_pen={sp:+.3f})", abs(sp) < 1e-9)
sp, win = run(2.0, hit_step=13, clock="frames", frames_per_step=10)
check(f"clock=frames, movement-only: hit 120 frames (2.0 s) after -> penalty (spec_pen={sp:+.3f})", abs(sp + 0.10) < 1e-9)
sp, win = run(2.0, hit_step=14, clock="frames", frames_per_step=10)
check(f"clock=frames, movement-only: hit 130 frames (2.17 s) after -> NO penalty (spec_pen={sp:+.3f})", abs(sp) < 1e-9)
mixed = lambda t: 10 if t % 2 else 6            # alternating movement / attack: 8 frames per step on average
sp, win = run(2.0, hit_step=16, clock="frames", frames_per_step=mixed)   # 15 steps after the special: 15*8 = 120 frames
check(f"clock=frames, mixed 6/10: hit 120 frames after -> penalty (spec_pen={sp:+.3f})", abs(sp + 0.10) < 1e-9)
sp, win = run(2.0, hit_step=17, clock="frames", frames_per_step=mixed)   # 16 steps: 128 frames
check(f"clock=frames, mixed 6/10: hit 128 frames after -> NO penalty (spec_pen={sp:+.3f})", abs(sp) < 1e-9)
sp, win = run(2.0, hit_step=25, clock="frames", frames_per_step=lambda t: 6 + (200 if t == 20 else 0))   # a transport stall adds 200 frames
check(f"clock=frames, 200-frame stall inside the window -> NO penalty (spec_pen={sp:+.3f})", abs(sp) < 1e-9)
# ---- finding 2: net telemetry = own - mean(others). Simultaneous hit: learner -0.1, seats 0 and 2 -0.2 each, caster (3) unhurt.
e = make_env(2.0, "frames"); e._zs = {"raw": 0.0, "opp_mean": 0.0, "adj": 0.0, "dealt_nn": 0.0, "n": 0}
pos = [(50, 0, 0), (0, 0, 0), (-50, 0, 0), (100, 0, 0)]
def st(ps, frame): return {"players": [{"pos": p, "gems": 0, "form": 0} for p in pos], "pstate": list(ps), "frame": frame}
h = [1.0] * 4
prev = st([0, 0, 0, 0], 0); s = st([0, 0, 0, 26], 6); e._zero_sum_reward(prev, h, s, list(h), {}); prev = s
s = st([0, 0, 0, 0], 12); nh = [0.8, 0.9, 0.8, 1.0]; e._zero_sum_reward(prev, h, s, nh, {})
raw, net = e._zs.get("spec_pen", 0.0), e._zs.get("spec_net", 0.0)
check(f"net telemetry: raw learner spec_pen {raw:+.3f}, net (own - mean others) {net:+.3f} -> net is POSITIVE when opponents are penalized more", abs(raw + 0.10) < 1e-9 and abs(net - (-0.10 - (-0.2 - 0.2 + 0.0) / 3)) < 1e-9)

# ---- Sep 29 (Blake: learner-only attribution fix): the decode and the reward branch
import ps2_addr as A
def own(phys): return FFASelfPlayEnv._owner_of(phys)
b0 = (A.PLAYER_MAT[0] - 0x490) & 0x0FFFFFFF
check("owner_of: P1 object start -> seat 0", own(b0) == 0)
check("owner_of: P1 object last byte -> seat 0", own(b0 + 0x3937) == 0)
check("owner_of: one past P1 = P2 start -> seat 1", own(b0 + 0x3938) == 1)
check("owner_of: P4 PLAYER_MAT itself -> seat 3", own(A.PLAYER_MAT[3] & 0x0FFFFFFF) == 3)
check("owner_of: a projectile object (0x0c50d194) -> None", own(0x0C50D194) is None)
check("owner_of: null -> None", own(0) is None)
# reward branch under attrib: monkeypatch the RAM reader
F.SPECIAL_ATTRIB = True
try:
    e = make_env(2.0, "frames"); e._zs = {"raw": 0.0, "opp_mean": 0.0, "adj": 0.0, "dealt_nn": 0.0, "n": 0}
    pos = [(50, 0, 0), (0, 0, 0), (-50, 0, 0), (5000, 0, 0)]          # caster (seat 3) is FAR: the radius rule would never fire
    def st2(ps, frame): return {"players": [{"pos": p, "gems": 0, "form": 0} for p in pos], "pstate": list(ps), "frame": frame}
    h = [1.0] * 4
    prev = st2([0, 0, 0, 0], 0); s = st2([0, 0, 0, 26], 6); e._zero_sum_reward(prev, h, s, list(h), {}); prev = s
    e._hit_attacker = lambda k: 3                                       # the game says seat 3 hit the learner
    s = st2([0, 0, 0, 0], 60); nh = [0.8, 0.9, 0.8, 1.0]; e._zero_sum_reward(prev, h, s, nh, {})
    check(f"attrib: far caster (5000 u) in window, game attributes the hit -> learner penalized (spec_pen={e._zs.get('spec_pen',0):+.3f})", abs(e._zs.get("spec_pen", 0.0) + 0.10) < 1e-9)
    check(f"attrib: opponents get NO special term -> spec_net == spec_pen ({e._zs.get('spec_net',0):+.3f})", abs(e._zs.get("spec_net", 0.0) - e._zs.get("spec_pen", 0.0)) < 1e-9)
    check(f"attrib: spec_dmg accumulates the attributed damage ({e._zs.get('spec_dmg',0):.2f})", abs(e._zs.get("spec_dmg", 0.0) - 0.10) < 1e-9)
    e2 = make_env(2.0, "frames"); e2._zs = {"raw": 0.0, "opp_mean": 0.0, "adj": 0.0, "dealt_nn": 0.0, "n": 0}
    prev = st2([0, 0, 0, 0], 0); s = st2([0, 0, 0, 26], 6); e2._zero_sum_reward(prev, h, s, list(h), {}); prev = s
    e2._hit_attacker = lambda k: 0                                      # hit by seat 0, who is NOT in a special
    s = st2([0, 0, 0, 0], 60); e2._zero_sum_reward(prev, h, s, [0.8, 0.9, 0.8, 1.0], {})
    check(f"attrib: hit by a non-casting seat while another seat casts -> NO penalty (spec_pen={e2._zs.get('spec_pen',0):+.3f}); attr counted", abs(e2._zs.get("spec_pen", 0.0)) < 1e-9 and e2._zs.get("attr_p", 0) == 1)
    e3 = make_env(2.0, "frames"); e3._zs = {"raw": 0.0, "opp_mean": 0.0, "adj": 0.0, "dealt_nn": 0.0, "n": 0}
    prev = st2([0, 0, 0, 0], 0); s = st2([0, 0, 0, 26], 6); e3._zero_sum_reward(prev, h, s, list(h), {}); prev = s
    e3._hit_attacker = lambda k: None                                   # unowned hazard
    s = st2([0, 0, 0, 0], 60); e3._zero_sum_reward(prev, h, s, [0.8, 0.9, 0.8, 1.0], {})
    check(f"attrib: unowned source -> NO penalty, attr_n counted ({e3._zs.get('attr_n',0)})", abs(e3._zs.get("spec_pen", 0.0)) < 1e-9 and e3._zs.get("attr_n", 0) == 1)
finally:
    F.SPECIAL_ATTRIB = False

print(f"special window test: {fails} failures (window {SPECIAL_WINDOW:g}s)")
sys.exit(1 if fails else 0)
