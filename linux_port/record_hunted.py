# record_hunted.py <model.zip> <slots> <out.mp4> <instance> -- record the bot vs two hunter bots + one lv8 CPU (states_mixed 30-43) until one win and one loss (Oct 11 2026). Needs the obs-v4 contract env flags.
import os, sys, json, subprocess, shutil, tempfile
sys.path.insert(0, ".")
os.environ.update(PS2_HUNTER_SEATS="0,2", PS2_FFA_SEATS="0,2", PS2_FFA_MAX_STEPS="6000")
for k in ("PS2_HUNTER_P", "PS2_ZERO_SUM", "PS2_START_HEALTH", "PS2_DRILL_DIR", "PS2_DRILL_P"): os.environ.pop(k, None)
import numpy as np, torch as th
th.set_num_threads(1)
from ffa_selfplay_env import FFASelfPlayEnv
from recurrent_policy import load_model, PolicyRunner
from obs_stack import stack_for, FrameStack   # Oct 13 2026: stack_for = kd_for + PS2_OBS_STACK check
model_path, slots, out, inst = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], sys.argv[3], int(sys.argv[4])
pool = tempfile.mkdtemp(prefix="rec_hunt_"); os.symlink(os.path.abspath(model_path), os.path.join(pool, "opp.zip"))
env = FFASelfPlayEnv(core_path=os.path.expanduser("~/cores/flycast_libretro.so"), game_path=os.path.abspath("../Power Stone 2 (USA).chd"),
                     states_dir="./states_mixed", state_slots=slots, instance_id=inst, bridge_dir=os.path.abspath(f"bridge_eval_{inst}"),
                     pool_dir=pool, opp_deterministic=True)
model = load_model(model_path); runner = PolicyRunner(model); env.set_action_mode(int(model.action_space.n))
k_, d_ = stack_for(model); fs = FrameStack(k_, d_) if k_ > 1 else None
env._legacy_proj_main = env._legacy_proj = (d_ == 122); env._legacy_item_main = env._legacy_item = (d_ <= 160)
br = env._lr_bridge; emu = br.emu; h, w = emu.get_shape(); buf = np.zeros((h, w, 3), np.uint8)
ff = shutil.which("ffmpeg")
proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", "60", "-i", "-",
                         "-vf", "scale=480:360:flags=neighbor,fps=30", "-c:v", "libx264", "-preset", "medium", "-crf", "30", "-pix_fmt", "yuv420p", out],
                        stdin=subprocess.PIPE)
_cls = type(br); _orig = _cls.run_frames
def run_rec(self, n):
    for _ in range(n):
        _orig(self, 1); emu.get_frame(buf, w, h); proc.stdin.write(buf[::-1].tobytes())
_cls.run_frames = run_rec   # class-level: the hunter-tap wrapper sets/deletes an instance attribute on top of this
wins = losses = 0
for ep in range(8):
    env.STATE_SLOTS = [slots[ep % len(slots)]]; env._preroll_next = (ep * 37) % 240
    obs = env.reset()[:d_]; obs = fs.reset(obs) if fs else obs; runner.reset(); done, info = False, {}
    while not done:
        obs, r, done, info = env.step(runner.act(obs, deterministic=True)); obs = obs[:d_]; obs = fs.push(obs) if fs else obs
    br.run_frames(90)
    res = info.get("result"); wins += res == "win"; losses += res != "win"
    print(f"[rec] ep {ep+1} slot {env.STATE_SLOTS[0]} {res} len={env.steps} ko={(env._hunt or {}).get('ko')}", flush=True)
    if wins >= 1 and losses >= 1: break
proc.stdin.close(); proc.wait(); print("[rec] saved", out, "wins", wins, "losses", losses, flush=True); os._exit(0)
