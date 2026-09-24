"""Sep 23 2026 obs v3 unit test (no emulator): a synthetic v8 line (93 fields) goes through the real
parser and the real observation builder; checks the 38 new dims, the third projectile slot, and that
the first 122 dims are identical to a v7 line's obs. Run with PS2_OBS_V3=1 PS2_OBS_V2=1. Exit 1 on failure."""
import os, sys, tempfile
import numpy as np
assert os.environ.get("PS2_OBS_V3") == "1", "run with PS2_OBS_V3=1"
from powerstone_env_libretro import PowerStoneEnvLibretro as Env

def make_env():
    e = Env.__new__(Env)
    e.SLOT_META = dict(Env.SLOT_META); e.AGENT_PLAYER = 2; e._active_opp = [0, 2, 3]
    e._episode_slot = 3; e.last_action = 0; e._my_g_int = 0; e._form_timer = 0
    e.baseline = [1000.0] * 4
    return e

def v7_line(players, proj=((0,)*5, (0,)*5), extra=""):
    f = ["100", "1000", "900", "800", "700"]
    for (x, y, z) in players:
        f += [f"{x}", f"{y}", f"{z}", "1", "0"]
    f += ["0", "0"] + ["0"] * 18                       # legacy g1 g2, 6 stone triples
    f += ["0", "1", "2", "3"] + ["0", "0", "1", "0"] + ["0", "0", "50", "0"] + ["0"] * 4   # gems, form, meter, item
    for p in proj:
        f += [f"{v}" for v in p]
    f += ["2", "0", "100", "200", "0", "0", "0", "0"]  # chest block
    if extra:
        f += extra.split(",")
    f += ["7"]                                          # ack LAST
    return ",".join(f)

players = [(0, 0, 0), (100, 0, 100), (400, 0, 100), (1000, 0, -500)]   # P2 = bot at (100,100)
# opponents nearest-first from P2: P1 (dist 141), P3 (300), P4 (1082)
proj = ((300, 0, 300, 1200, 0), (900, 0, 900, 600, 600))
line7 = v7_line(players, proj)
line8 = v7_line(players, proj, extra="7,32,26,1,0,38,0,0,2000,0,2000,-600,600")  # state P1..P4, stun P1..P4, proj3 (FARTHEST -> slot 3; slots sort nearest-first)
fails = 0
def check(cond, msg):
    global fails
    if not cond:
        fails += 1; print("FAIL", msg)

e = make_env()
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
    fh.write(line7); p7 = fh.name
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
    fh.write(line8); p8 = fh.name
Base = Env.__mro__[1]                                   # PowerStoneEnvV6 (file-based parser)
e._state_file = p7; s7 = Base._parse_state_once(e)
e._state_file = p8; s8 = Base._parse_state_once(e)
check(s7 is not None and s7.get("v7") and "pstate" not in s7, "v7 line parses without v3 fields")
check(s8 is not None and s8.get("v8") and s8["ack"] == 7, f"v8 line parses, ack last ({s8 and s8.get('ack')})")
check(s8["pstate"] == [7, 32, 26, 1] and s8["pstun"] == [0, 38, 0, 0], f"state/stun parsed {s8['pstate']} {s8['pstun']}")
check(len(s8["proj"]) == 3 and s8["proj"][2][0] == 2000, f"third projectile parsed {s8['proj']}")
o7 = e._observe(s7, s7); o8 = e._observe(s8, s8)
check(o8.shape[0] == 160 and o7.shape[0] == 160, f"obs dim {o8.shape}")
check(np.array_equal(o7[:122], o8[:122]), "first 122 dims identical between v7 and v8 lines")
check(not o7[122:].any(), "v7 line leaves the v3 block at zero")
# self (P2): stun 38 -> 0.95, state 32 -> class 3 (hit)
check(abs(o8[122] - 38 / 40) < 1e-6 and o8[123 + 3] == 1.0 and o8[123:130].sum() == 1.0, f"self block {o8[122:130]}")
# opp1 = P1: stun 0, state 7 -> class 2 (attack); opp2 = P3: state 26 -> class 5; opp3 = P4: state 1 -> class 0
check(o8[130] == 0 and o8[131 + 2] == 1.0, f"opp1 block {o8[130:138]}")
check(o8[139 + 5] == 1.0, f"opp2 block {o8[138:146]}")
check(o8[147 + 0] == 1.0, f"opp3 block {o8[146:154]}")
# third projectile at 154: present, dx=(2000-100)/POS_SCALE, vx=-600/1200
check(o8[154] == 1.0 and o8[155] > 0 and abs(o8[158] + 600 / e.PROJ_VEL_SCALE) < 1e-6, f"proj3 block {o8[154:160]}")
check(o8[81] == 1.0 and o8[87] == 1.0, "first two projectile slots still populated")
print(f"obs v3 unit test: {fails} failures")
sys.exit(1 if fails else 0)
