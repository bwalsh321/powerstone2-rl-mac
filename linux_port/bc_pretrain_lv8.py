"""Behavioral cloning: Blake's demos -> a PPO-resumable SB3 model.

HANDOFF Sec 20, imitation pipeline step 3 of 3. Loads every demos/*.npz
from record_demo.py, trains the SAME MlpPolicy architecture train_v6.py
uses via cross-entropy on Blake's actions, and saves powerstone_v6_bc.zip.

Tuned for a SMALL dataset (~10k decisions from 15-20 min of play):
val split by contiguous blocks (no shuffle leakage between neighboring,
near-identical frames), early stopping on val loss, entropy bonus so the
policy does not collapse to overconfident spikes PPO would then have to
un-learn (PPO fine-tuning needs exploration mass to work with).

Usage (project root, training venv):
    python bc_pretrain.py
Then to launch the BC-seeded PPO leg:
    copy powerstone_v6_bc.zip powerstone_v6_ppo.zip
    python train_v6.py            <- prints "Resuming from ..." (wanted!)

256-LINEAGE usage (Aug 22 — the Leg P recipe, no bridge needed, ~30-60min
CPU with early stopping):
    python bc_pretrain.py demos:3,demos_v4corpus --arch 256x256
    -> saves powerstone_v6_bc256.zip, then:  start_leg_256
The human dir rides at repeat 3 (~11% of volume) for execution texture;
the v4 corpus carries scale. Expect val_acc ~77% (the capacity test's
number) — meaningfully above the 64x64 net's ~75.5% on the same data.

NOTE: never write powerstone_v6_ppo.zip while a trainer is running.

CORPUS CAVEAT (Sep 10 2026 external audit, verified): in every recorded
corpus (demos, demos_lv8, demos_v4corpus) the self-velocity features
obs[4:6] are exactly 0 in >98% of rows, because the recorders compared
near-adjacent states instead of the ACTION_FRAMES window the live env uses.
Online, those features are nonzero whenever anyone moves. So a clone
trained here has never seen the velocity signal it gets at deployment, and
"BC failed because of covariate shift" is only part of the story. Fix the
recorder window (and align the last-action timing, see powerstone_env_v6
.step) BEFORE recording more demonstrations or judging DAgger.
"""

import glob
import os
import sys

import gym
import numpy as np
import torch

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---- Aug 22: 256-LINEAGE SUPPORT ------------------------------------
# `--arch 256x256` builds the wider net (capacity test, HANDOFF Aug 22:
# 64x64 UNDERFITS the corpus — held-out NLL 0.397 vs 0.321 at 256x256;
# 512 bought nothing at this corpus size). Output name gains the arch
# so lineages can never be confused on disk.
# Demo-dir arg now accepts comma-separated dirs with an optional
# per-dir repeat: "demos:3,demos_v4corpus" loads Blake's 9,943 human
# pairs three times alongside the 247k v4-corpus pairs (~11% human by
# volume) — the human data carries the execution texture the ladder
# cannot demonstrate, and 4% unweighted would drown it.
_args = sys.argv[1:]
NET_ARCH = None
if "--arch" in _args:
    _i = _args.index("--arch")
    NET_ARCH = [int(x) for x in _args[_i + 1].split("x")]
    del _args[_i:_i + 2]
OUT = os.path.join(ROOT, "powerstone_v6_bclv8_"
                   + ("" if not NET_ARCH else str(NET_ARCH[0])))

OBS_DIM, N_ACT = 122, 10
BATCH = 256
MAX_EPOCHS = 60
PATIENCE = 6            # early stop: epochs without val improvement
LR = 3e-4
ENT_BONUS = 0.01        # keep some probability mass off the argmax
VAL_FRAC = 0.10
ACTION_NAMES = ["up", "down", "left", "right", "jump", "grab",
                "attack", "throw", "pf1", "pf2"]


class _SpecEnv(gym.Env):
    """Spaces-only stand-in so PPO() can be constructed without the bridge."""
    observation_space = gym.spaces.Box(low=-5.0, high=5.0,
                                       shape=(OBS_DIM,), dtype=np.float32)
    action_space = gym.spaces.Discrete(N_ACT)

    def reset(self):
        return np.zeros(OBS_DIM, dtype=np.float32)

    def step(self, action):
        raise RuntimeError("spec env is not steppable")


def load_demos():
    # arg: demo dir(s), comma-separated, each optionally "dir:repeat"
    # (default "demos"; e.g. "demos:3,demos_v4corpus" for the 256 lineage).
    # Returns per-dir (obs, act) lists so the val split can take a
    # contiguous tail from EACH corpus — a single global tail would make
    # validation 100% last-loaded-corpus.
    spec = _args[0] if _args else "demos"
    per_dir = []
    for part in spec.split(","):
        ddir, _, rep = part.partition(":")
        rep = int(rep) if rep else 1
        files = sorted(glob.glob(os.path.join(ROOT, ddir, "demo_*.npz")))
        if not files:
            raise SystemExit(f"no {ddir}/demo_*.npz found")
        obs, act = [], []
        for f in files:
            d = np.load(f)
            obs.append(d["obs"])
            act.append(d["action"])
            print(f"[bc] {ddir}/{os.path.basename(f)}: "
                  f"{len(d['action'])} pairs x{rep}")
        per_dir.append((np.concatenate(obs), np.concatenate(act), rep))
    return per_dir


def main():
    per_dir = load_demos()
    # contiguous tail PER CORPUS as validation -- neighboring frames are
    # nearly identical, so a random split would leak train into val; and
    # the val tail is taken BEFORE the repeat factor so repeated copies
    # of a val frame can never sit in train.
    Xt_l, yt_l, Xv_l, yv_l = [], [], [], []
    for X, y, rep in per_dir:
        n_val = max(64, int(len(y) * VAL_FRAC))
        for _ in range(rep):
            Xt_l.append(X[:-n_val]); yt_l.append(y[:-n_val])
        Xv_l.append(X[-n_val:]); yv_l.append(y[-n_val:])
    Xt, yt = np.concatenate(Xt_l), np.concatenate(yt_l)
    Xv, yv = np.concatenate(Xv_l), np.concatenate(yv_l)
    n = len(yt) + len(yv)
    print(f"[bc] total {n} pairs (train {len(yt)} / val {len(yv)})")
    counts = np.bincount(yt, minlength=N_ACT)
    print("[bc] action mix: " + "  ".join(
        f"{a}={c}" for a, c in zip(ACTION_NAMES, counts) if c))

    # inverse-frequency class weights, softened -- movement dominates any
    # demo; without weighting the rare-but-crucial actions (grab, pf) drown
    w = 1.0 / np.sqrt(np.maximum(counts, 1))
    w = w / w.sum() * N_ACT
    w_t = torch.as_tensor(w, dtype=torch.float32)

    # KICKSTART MODE (Aug 13): pass a model zip as argv[2] to apply the BC
    # epochs to an EXISTING policy instead of a fresh net -- injects the
    # demo behavior while keeping everything the model already knows.
    # Uses a gentler LR so the surgery does not scramble trained skills.
    init_zip = _args[1] if len(_args) > 1 else None
    if init_zip:
        if NET_ARCH:
            raise SystemExit("[bc] --arch with KICKSTART makes no sense — "
                             "an existing zip already fixes the architecture")
        model = PPO.load(init_zip.replace(".zip", ""),
                         env=DummyVecEnv([_SpecEnv]), device="cpu")
        globals()["LR"] = 1e-4
        print(f"[bc] KICKSTART: injecting demos into {init_zip} (LR=1e-4)")
    else:
        pk = dict(net_arch=NET_ARCH) if NET_ARCH else None
        if NET_ARCH:
            print(f"[bc] FRESH NET, net_arch={NET_ARCH} -> {OUT}.zip")
        # device="cpu" is MANDATORY here (Aug 22 crash): the 5070 Ti is
        # detected by torch but sm_120 is unsupported by this build, so a
        # cuda-placed model dies on the first forward pass with a
        # cpu/cuda:0 device mismatch. The KICKSTART path above already
        # pins cpu; this path was the one that forgot.
        model = PPO("MlpPolicy", DummyVecEnv([_SpecEnv]), verbose=0,
                    n_steps=2048, batch_size=64, learning_rate=3e-4,
                    gamma=0.999, ent_coef=0.01, target_kl=0.03,
                    policy_kwargs=pk, device="cpu")
    policy = model.policy
    policy.set_training_mode(True)
    opt = torch.optim.Adam(policy.parameters(), lr=LR)

    def batches(Xa, ya, shuffle=True):
        idx = np.arange(len(ya))
        if shuffle:
            np.random.shuffle(idx)
        for i in range(0, len(idx), BATCH):
            j = idx[i:i + BATCH]
            yield (torch.as_tensor(Xa[j]), torch.as_tensor(ya[j]))

    def eval_val():
        policy.set_training_mode(False)
        tot, correct, lsum = 0, 0, 0.0
        with torch.no_grad():
            for xb, yb in batches(Xv, yv, shuffle=False):
                dist = policy.get_distribution(xb)
                lp = dist.log_prob(yb)
                lsum += float(-lp.sum())
                correct += int((dist.distribution.probs.argmax(1) == yb).sum())
                tot += len(yb)
        policy.set_training_mode(True)
        return lsum / tot, correct / tot

    best, best_state, stale = float("inf"), None, 0
    for epoch in range(1, MAX_EPOCHS + 1):
        for xb, yb in batches(Xt, yt):
            dist = policy.get_distribution(xb)
            ce = -(dist.log_prob(yb) * w_t[yb]).mean()
            ent = dist.entropy().mean()
            loss = ce - ENT_BONUS * ent
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
            opt.step()
        vloss, vacc = eval_val()
        marker = ""
        if vloss < best - 1e-4:
            best, stale = vloss, 0
            best_state = {k: v.detach().clone()
                          for k, v in policy.state_dict().items()}
            marker = "  <- best"
        else:
            stale += 1
        print(f"[bc] epoch {epoch:2d}  val_loss {vloss:.4f}  "
              f"val_acc {vacc:.1%}{marker}")
        if stale >= PATIENCE:
            print(f"[bc] early stop (no val improvement in {PATIENCE} epochs)")
            break

    if best_state is not None:
        policy.load_state_dict(best_state)
    policy.set_training_mode(False)

    # per-action val accuracy -- the interesting rows are grab/attack:
    # does the clone reach for stones when YOU would?
    with torch.no_grad():
        dist = policy.get_distribution(torch.as_tensor(Xv))
        pred = dist.distribution.probs.argmax(1).numpy()
    print("[bc] per-action val accuracy:")
    for a in range(N_ACT):
        m = yv == a
        if m.sum():
            print(f"       {ACTION_NAMES[a]:>7}: "
                  f"{(pred[m] == a).mean():.1%}  (n={m.sum()})")

    model.save(OUT)
    print(f"\n[bc] saved {OUT}.zip")
    if NET_ARCH:
        print("[bc] 256 lineage: launch the PPO leg with  start_leg_256")
    else:
        print("[bc] to launch the BC-seeded PPO leg:")
        print("       copy powerstone_v6_bc.zip powerstone_v6_ppo.zip")
        print("       python train_v6.py")


if __name__ == "__main__":
    main()
