"""obs_overlay.py — END-TO-END visual validation of obs v3 (Sep 23 2026). Runs the REAL env
(PowerStoneEnvLibretro, PS2_OBS_V3=1) with a policy acting, and every --every steps saves the game
frame with the policy's OWN observation decoded on top: self stun/state class, the three nearest
opponents' stun/state class (with which player each slot is), and the three projectile slots.
Frames -> <out>/overlay/f*.png (tile them with `ram_scan.py sheets --out <out>`), values -> <out>/obs.csv.
    PS2_OBS_V3=1 PS2_OBS_V2=1 PYTHONPATH=../sdlarch-rl/p4:. python obs_overlay.py --model X.zip --out scan/ov1 --instance 12"""
import argparse, os, numpy as np, torch as th
from PIL import Image, ImageDraw
from stable_baselines3 import PPO
from obs_stack import kd_for, FrameStack
from powerstone_env_libretro import PowerStoneEnvLibretro
CLS = ["idle/walk", "AIR", "ATTACK", "HIT", "XFORM", "SPECIAL", "other"]
SEAT = {0: "1P-red Pride", 1: "2P-yel Falcon", 2: "3P-blu Ryoma", 3: "4P-grn Accel"}
ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--steps", type=int, default=900); ap.add_argument("--every", type=int, default=3)
ap.add_argument("--instance", type=int, default=12); ap.add_argument("--slot", type=int, default=3)
a = ap.parse_args()
assert os.environ.get("PS2_OBS_V3") == "1"
os.makedirs(os.path.join(a.out, "overlay"), exist_ok=True)
M = PPO.load(a.model.removesuffix(".zip"), device="cpu"); K, D = kd_for(M); assert D == 160
core = os.environ.get("PS2_CORE") or os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" if os.uname().sysname == "Darwin" else "~/cores/flycast_libretro.so")
env = PowerStoneEnvLibretro(core_path=core, game_path="../Power Stone 2 (USA).chd", states_dir="./states",
                            state_slots=[a.slot], instance_id=a.instance, bridge_dir=os.path.abspath(f"./bridge_probe_{a.instance}"))
emu = env._lr_bridge.emu; H, W = emu.get_shape(); buf = np.zeros((H, W, 3), np.uint8)
fs = FrameStack(K, 160)
csv = open(os.path.join(a.out, "obs.csv"), "w")
csv.write("step,ep,frame,self_hp,self_stun,self_cls,self_raw_state,self_raw_stun," +
          ",".join(f"opp{k}_seat,opp{k}_hp,opp{k}_stun,opp{k}_cls,opp{k}_raw_state,opp{k}_raw_stun" for k in (1, 2, 3)) +
          ",proj1,proj1_dx,proj1_dz,proj1_vx,proj1_vz,proj2,proj2_dx,proj2_dz,proj3,proj3_dx,proj3_dz,proj_classes,pool_fast\n")
PS, VS = env.POS_SCALE if hasattr(env, "POS_SCALE") else 1.0, env.PROJ_VEL_SCALE
import powerstone_env_v6 as PE
PS = PE.POS_SCALE
def decode(o, s):
    self_cls = int(np.argmax(o[123:130])) if o[123:130].any() else -1
    opps = env._opps(s)[:3] if s is not None else []
    rows = [("self", 1, o[0], o[122] * 40, self_cls)]
    for k in range(3):
        b = 130 + 8 * k
        seat = opps[k][1] if k < len(opps) else -1
        hp = o[18 + 13 * k + 7]
        cls = int(np.argmax(o[b + 1:b + 8])) if o[b + 1:b + 8].any() else -1
        rows.append((f"opp{k+1}", seat, hp, o[b] * 40, cls))
    projs = [(o[81], o[82] * PS, o[83] * PS, o[85] * VS, o[86] * VS), (o[87], o[88] * PS, o[89] * PS, o[91] * VS, o[92] * VS),
             (o[154], o[155] * PS, o[156] * PS, o[158] * VS, o[159] * VS)]
    return rows, projs
import ps2_addr as A, struct
ram = env._lr_bridge.ram; base = A.RAM_BASE + A.RAM_DELTA
pool_idx = (A.POOL_BASE - base) + np.arange(A.POOL_SLOTS) * A.POOL_STRIDE
def pool_read():
    act = ram[pool_idx + A.POOL_ACTIVE]
    cls = (ram[pool_idx + A.POOL_CLASS].astype(np.uint32) | ram[pool_idx + A.POOL_CLASS + 1].astype(np.uint32) << 8
           | ram[pool_idx + A.POOL_CLASS + 2].astype(np.uint32) << 16 | ram[pool_idx + A.POOL_CLASS + 3].astype(np.uint32) << 24)
    pp = np.zeros((A.POOL_SLOTS, 3), np.float32)
    for j in np.flatnonzero(act == 1):
        o = int(pool_idx[j]); pp[j] = [struct.unpack_from("<f", ram, o + A.POOL_POS[i])[0] for i in range(3)]
    return act, cls, pp
prev_pool = None
def pool_fast():
    """Independent check: live pool objects moving >= 700 u/s (>= 300 in xz) since the previous step."""
    global prev_pool
    act, cls, pp = pool_read(); out = []
    if prev_pool is not None:
        pa, pc, ppp = prev_pool
        same = (act == 1) & (pa == 1) & (cls == pc)
        dp = pp - ppp; sp = np.sqrt((dp ** 2).sum(-1)) * 10.0; spxz = np.sqrt(dp[:, 0] ** 2 + dp[:, 2] ** 2) * 10.0
        for j in np.flatnonzero(same & (sp >= 700)):
            c = int(cls[j])
            if c in A.PROJ_EXCLUDE or c in A.PROJ_EXCLUDE_V3 or any(lo <= c < hi for lo, hi in A.PROJ_EXCLUDE_BANDS + A.PROJ_EXCLUDE_BANDS_V3):
                continue
            out.append(f"{c:#x}:{sp[j]:.0f}")
    prev_pool = (act.copy(), cls.copy(), pp.copy())
    return "|".join(out)
obs = env.reset(); so = fs.reset(obs); ep = 1; n = 0
with th.no_grad():
    while n < a.steps:
        act, _ = M.predict(so, deterministic=False)
        obs, r, done, info = env.step(act); n += 1
        s = env.prev
        rows, projs = decode(obs, s)
        raw_st = s.get("pstate", [0] * 4) if s else [0] * 4; raw_sn = s.get("pstun", [0] * 4) if s else [0] * 4
        pcls_csv = "|".join(f"{c:#x}" for c in getattr(env._lr_synth, "_proj_cache_cls", []))
        pfast = pool_fast()
        csv.write(f"{n},{ep},{s['frame'] if s else 0},{rows[0][2]:.2f},{rows[0][3]:.0f},{rows[0][4]},{raw_st[1]},{raw_sn[1]}," +
                  ",".join(f"{rr[1]},{rr[2]:.2f},{rr[3]:.0f},{rr[4]},{raw_st[rr[1]] if rr[1] >= 0 else ''},{raw_sn[rr[1]] if rr[1] >= 0 else ''}" for rr in rows[1:]) +
                  f",{projs[0][0]:.0f},{projs[0][1]:.0f},{projs[0][2]:.0f},{projs[0][3]:.0f},{projs[0][4]:.0f},{projs[1][0]:.0f},{projs[1][1]:.0f},{projs[1][2]:.0f},{projs[2][0]:.0f},{projs[2][1]:.0f},{projs[2][2]:.0f},{pcls_csv},{pfast}\n")
        if n % a.every == 0:
            emu.get_frame(buf, W, H); im = Image.fromarray(buf[::-1]); dr = ImageDraw.Draw(im)
            dr.rectangle((0, 0, W, 90), fill=(0, 0, 0))
            dr.text((4, 2), f"step {n} ep {ep}  frame {s['frame'] if s else 0}  (what the BOT's observation says)", fill=(255, 255, 255))
            for i, (lab, seat, hp, stun, cls) in enumerate(rows):
                dr.text((4, 14 + 12 * i), f"{lab:5s} {SEAT.get(seat, '?'):16s} hp={hp:4.2f} stun={stun:2.0f} {CLS[cls] if cls >= 0 else '(none)'}",
                        fill=(255, 255, 0) if i == 0 else (220, 220, 220))
            pcls = list(getattr(env._lr_synth, "_proj_cache_cls", []))
            pt = "  ".join(f"P{i+1}:{'YES' if p[0] > 0 else 'no'}" + (f" d=({p[1]:.0f},{p[2]:.0f}) v=({p[3]:.0f},{p[4]:.0f}) {pcls[i]:#x}" if p[0] > 0 and i < len(pcls) else "") for i, p in enumerate(projs))
            dr.text((4, 64), "projectile slots " + pt, fill=(120, 255, 255))
            im.save(os.path.join(a.out, "overlay", f"f{n:05d}.png"))
        so = fs.push(obs)
        if done:
            obs = env.reset(); so = fs.reset(obs); ep += 1
csv.close(); print(f"[overlay] {n} steps, {ep} episodes, frames in {a.out}/overlay")
