"""measure_dmg_attrib.py -- how often does the zero-sum "nearest alive seat" damage credit agree with the game's own
hit-source pointer (FFASelfPlayEnv._hit_attacker, PLAYER_MAT+0x32E4)? (Oct 7 2026, reward-cleanup bundle, item 1.)

Runs the UNMODIFIED reward path (PS2_DMG_ATTRIB unset): the env's _zero_sum_reward is wrapped so that, on every step,
every present seat's health drop is classified BEFORE the original reward runs (same prev/now states, RAM read at the
same point the special-attrib term reads it):
  heur  = nearest alive other seat (xz) -- the credit the reward uses today
  hs    = _hit_attacker(victim) -- None when the pointer is null / unowned / self / outside RAM
and the learner-credited damage under both rules ("hitsrc" = hs when it names a present seat, else heur).

    run.sh <tree> measure_dmg_attrib.py --instance 80 --steps 3000 --warm LEARNER.zip --pool POOL_DIR --out a.json
    python measure_dmg_attrib.py --merge a.json b.json
The learner is driven by --warm (stacked/recurrent, sampled actions), the policy seats by the pool (as in training).
"""
import argparse
import json
import os
import random
import sys

import numpy as np


def run(a):
    import torch as th
    th.set_num_threads(1)
    random.seed(a.seed); np.random.seed(a.seed); th.manual_seed(a.seed)
    from ffa_selfplay_env import FFASelfPlayEnv
    from obs_stack import StackedEnv, kd_for
    from recurrent_policy import load_model, PolicyRunner
    slots = list(range(a.slot_lo, a.slot_hi + 1))
    env = FFASelfPlayEnv(core_path=os.environ["PS2_CORE"], game_path=os.environ["PS2_GAME"],
                         states_dir=os.environ.get("PS2_STATES_DIR", "./states_mixed"), instance_id=a.instance,
                         state_slots=slots, bridge_dir=os.path.abspath(f"bridge_i{a.instance}"), pool_dir=a.pool)
    model = load_model(a.warm)
    K, _ = kd_for(model)
    env.set_action_mode(int(model.action_space.n))
    senv = StackedEnv(env, K) if K > 1 else env
    st = dict(drops=0, agree=0, disagree=0, hs_none=0, hs_absent=0, dmg=0.0, dmg_agree=0.0, dmg_disagree=0.0,
              dmg_hs_none=0.0, L_heur=0.0, L_hs=0.0, L_out=0.0, L_in=0.0,
              Lvict_drops=0, Lvict_agree=0, Lvict_disagree=0, Lvict_none=0,
              com_heur=0.0, com_hs=0.0)
    i = env._learner_idx
    orig = env._zero_sum_reward

    def wrapped(prev_s, prev_h, s, h, info, _o=orig):
        present = [k for k in env._present_seats() if k < len(h)]
        for k in present:
            drop = max(0.0, prev_h[k] - h[k])
            if drop <= 0.0:
                continue
            pk = prev_s["players"][k]["pos"]
            heur, bd = None, float("inf")
            for m in present:
                if m == k or not env._alive(prev_h[m]):
                    continue
                pm = prev_s["players"][m]["pos"]
                d = (pk[0] - pm[0]) ** 2 + (pk[2] - pm[2]) ** 2
                if d < bd:
                    heur, bd = m, d
            hs = env._hit_attacker(k)
            st["drops"] += 1; st["dmg"] += drop
            if hs is None:
                st["hs_none"] += 1; st["dmg_hs_none"] += drop; new = heur
            elif hs not in present:
                st["hs_absent"] += 1; st["dmg_hs_none"] += drop; new = heur
            elif hs == heur:
                st["agree"] += 1; st["dmg_agree"] += drop; new = hs
            else:
                st["disagree"] += 1; st["dmg_disagree"] += drop; new = hs
            if k == i:
                st["Lvict_drops"] += 1
                st["Lvict_none" if (hs is None or hs not in present) else
                   "Lvict_agree" if hs == heur else "Lvict_disagree"] += 1
            if heur == i:
                st["L_heur"] += drop
            if new == i:
                st["L_hs"] += drop
            if heur == i and new != i:
                st["L_out"] += drop
            if heur != i and new == i:
                st["L_in"] += drop
            if heur == 3:
                st["com_heur"] += drop
            if new == 3:
                st["com_hs"] += drop
        return _o(prev_s, prev_h, s, h, info)
    env._zero_sum_reward = wrapped
    runner = PolicyRunner(model)
    obs = senv.reset(); runner.reset()
    eps = 0
    for t in range(a.steps):
        act = runner.act(obs, deterministic=False)
        obs, r, done, info = senv.step(int(act))
        if done:
            eps += 1
            obs = senv.reset(); runner.reset()
    st["steps"], st["episodes"], st["instance"] = a.steps, eps, a.instance
    json.dump(st, open(a.out, "w"))
    print("[measure]", json.dumps(st), flush=True)


def merge(paths):
    t = {}
    for p in paths:
        for k, v in json.load(open(p)).items():
            if k != "instance":
                t[k] = t.get(k, 0) + v
    resolved = t["agree"] + t["disagree"]
    print(json.dumps(t))
    print(f"steps={t['steps']} episodes={t['episodes']} damage events={t['drops']} "
          f"(pointer resolved {resolved} = {resolved / max(1, t['drops']):.1%}, none/unowned {t['hs_none']}, "
          f"absent seat {t['hs_absent']})")
    print(f"agreement (resolved events): {t['agree'] / max(1, resolved):.1%} of events, "
          f"{t['dmg_agree'] / max(1e-9, t['dmg_agree'] + t['dmg_disagree']):.1%} of damage; "
          f"over ALL events incl. fallback: credit unchanged on {(t['agree'] + t['hs_none'] + t['hs_absent']) / max(1, t['drops']):.1%}")
    print(f"learner-credited damage: heuristic {t['L_heur']:.3f}, hitsrc {t['L_hs']:.3f} "
          f"(moved out {t['L_out']:.3f} = {t['L_out'] / max(1e-9, t['L_heur']):.1%} of heuristic credit, "
          f"moved in {t['L_in']:.3f} = {t['L_in'] / max(1e-9, t['L_heur']):.1%}; "
          f"net change {(t['L_hs'] - t['L_heur']) / max(1e-9, t['L_heur']):+.1%})")
    print(f"learner as victim: {t['Lvict_drops']} events, agree {t['Lvict_agree']}, disagree {t['Lvict_disagree']}, "
          f"fallback {t['Lvict_none']}; COM seat (P4) credit heuristic {t['com_heur']:.3f} -> hitsrc {t['com_hs']:.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", nargs="*")
    ap.add_argument("--instance", type=int, default=80)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--warm", default="")
    ap.add_argument("--pool", default="")
    ap.add_argument("--slot-lo", type=int, default=50)
    ap.add_argument("--slot-hi", type=int, default=68)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="dmg_attrib.json")
    a = ap.parse_args()
    if a.merge:
        merge(a.merge)
        sys.exit(0)
    run(a)
    sys.stdout.flush()
    os._exit(0)                       # skip the core's teardown abort
