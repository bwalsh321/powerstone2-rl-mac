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

def make_env(window_s):
    e = FFASelfPlayEnv.__new__(FFASelfPlayEnv)
    e._present_seats = lambda: [0, 1, 2, 3]
    e._learner_idx = 1
    e._episode_slot = 30                      # lv8 P4 COM slot -> level 8
    e.SLOT_META = F.ffa_slot_meta([30], FFASelfPlayEnv.SLOT_META)
    e._zs_gem = {}; e._zs = {"raw": 0.0, "opp_mean": 0.0, "adj": 0.0, "dealt_nn": 0.0, "n": 0}
    e._spec_win = int(round(window_s * 60.0 / e.ACTION_FRAMES)); e._spec_last = {}; e._spec_t = 0
    return e

def state(pstate, learner_pos=(0, 0, 0), caster_pos=(100, 0, 0)):
    pos = [(5000, 0, 5000), learner_pos, (-5000, 0, -5000), caster_pos]
    return {"players": [{"pos": p, "gems": 0, "form": 0} for p in pos], "pstate": list(pstate)}

def run(window_s, hit_step, caster_special_steps=(1,), n=40, dmg=0.10):
    e = make_env(window_s)
    h = [1.0, 1.0, 1.0, 1.0]
    prev = state([0, 0, 0, 0])                # the special is SEEN as a stepped frame (t=1), like the real loop
    for t in range(1, n):
        ps = [0, 0, 0, 26 if t in caster_special_steps else 0]
        s = state(ps)
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
print(f"special window test: {fails} failures (window {SPECIAL_WINDOW:g}s)")
sys.exit(1 if fails else 0)
