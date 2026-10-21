"""Adaptive handicap (Oct 19 2026; docs/NEXT_CHANGES.md IDEA QUEUE #1, after warlock.ai's Warcraft III agent, which
taxed the built-in AI after the agent lost and untaxed it after it won to keep training near 50/50).

Our learner wins ~68% of its 3-CPU training rounds (slots 50-68) and the CPUs are already at level 8 (the game's max),
so the LEARNER is handicapped instead: at reset on a handicapped slot its health is multiplied by h in [MIN, 1]
(on top of the PS2_START_HEALTH draw), and h follows the learner's results on those slots.

Flags (all training-only; read by ffa_selfplay_env.FFASelfPlayEnv; absent = off, bit-identical):
  PS2_HANDICAP=1            turn it on
  PS2_HANDICAP_TARGET=0.55  training win share the controller steers to
  PS2_HANDICAP_MIN=0.5      floor on h (ceiling is 1.0: never a bonus)
  PS2_HANDICAP_SLOTS=50-68  slots that are handicapped AND counted (bot-copy / hunter slots 30-43 are left alone)
  PS2_HANDICAP_STEP=0.01    controller gain: after each counted episode h -= STEP * (won - TARGET)
  PS2_HANDICAP_EMA=200      EMA window (episodes) of the logged win share (logging only, see below)
  PS2_HANDICAP_STATE=claude_bridge/handicap_state   carry-over folder ("" / "0" = no carry-over)

Update rule. After every counted episode (won = 1 for a win, 0 for a loss or timeout):
    h <- clamp(h - STEP * (won - TARGET), MIN, 1.0)
i.e. a win lowers h by STEP*(1-TARGET) (0.0045), a loss raises it by STEP*TARGET (0.0055). The expected move is zero
exactly when the win share equals TARGET, so that is the fixed point; h moves at most 0.01 per episode. This is the
warlock.ai per-result tax/untax, scaled so the rates balance at TARGET (a Robbins-Monro step). It is deliberately NOT
"step h by +-0.01 on the sign of a 200-episode EMA": each actor sees only ~330 counted episodes per leg (leg 204:
5,293 slot-50-68 rounds over 16 actors), and a sign rule on an EMA that lags ~200 episodes keeps pushing h in one
direction long after the true win share has crossed the target (up to ~2.0 of h per lag, i.e. clamp to clamp), so it
limit-cycles; test_handicap.py simulates both. With the per-result rule the time constant is ~1 / (STEP * dP/dh)
episodes (dP/dh ~ 0.5-1 per unit of h: ~100-200 episodes, under one leg per actor) and the steady-state wobble of h
from coin-flip noise is ~sqrt(STEP * p(1-p) / (2 dP/dh)) ~ 0.03-0.05.

The EMA (window PS2_HANDICAP_EMA) is the readable "how often is it winning on these slots" number in the logs; it does
not drive h.

Carry-over. Each env writes its state (h, ema, n) to <STATE>/hcap_i<instance>.json after every counted episode (tmp +
rename, so a reader never sees half a file). At start each env reads that folder ONCE and starts from the mean h / ema
of the files written within 6 h of the newest one (stale files from instances no longer used drop out). A missing
folder, an unreadable or corrupt file, or out-of-range numbers are skipped; nothing usable = h 1.0, ema TARGET.
"""
import glob
import json
import os

HOURS_FRESH = 6.0


def parse_slots(text):
    out = set()
    for part in str(text).split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-")
            out.update(range(int(lo), int(hi) + 1))
        elif part:
            out.add(int(part))
    return out


def enabled(environ=None):
    environ = os.environ if environ is None else environ
    return environ.get("PS2_HANDICAP", "0").strip() == "1"


class Handicap:
    def __init__(self, target=0.55, h_min=0.5, step=0.01, ema_window=200.0, slots=None, state_dir="", tag="0"):
        if not (0.0 < target < 1.0):
            raise ValueError(f"PS2_HANDICAP_TARGET={target} must be in (0, 1)")
        if not (0.0 < h_min <= 1.0):
            raise ValueError(f"PS2_HANDICAP_MIN={h_min} must be in (0, 1]")
        if not (step > 0.0) or not (ema_window >= 1.0):
            raise ValueError(f"PS2_HANDICAP_STEP={step} must be > 0 and PS2_HANDICAP_EMA={ema_window} >= 1")
        self.target, self.h_min, self.step, self.window = float(target), float(h_min), float(step), float(ema_window)
        self.slots = set(range(50, 69)) if slots is None else set(slots)
        self.state_dir = state_dir if state_dir not in ("", "0") else ""
        self.tag = str(tag)
        self.h, self.ema = 1.0, self.target
        self.n, self.wins = 0, 0           # counted episodes / wins in THIS process
        self.carried = 0                   # state files the start values were pooled from

    @classmethod
    def from_env(cls, tag="0", environ=None):
        e = os.environ if environ is None else environ
        hc = cls(target=float(e.get("PS2_HANDICAP_TARGET", "0.55") or 0.55),
                 h_min=float(e.get("PS2_HANDICAP_MIN", "0.5") or 0.5),
                 step=float(e.get("PS2_HANDICAP_STEP", "0.01") or 0.01),
                 ema_window=float(e.get("PS2_HANDICAP_EMA", "200") or 200),
                 slots=parse_slots(e.get("PS2_HANDICAP_SLOTS", "50-68") or "50-68"),
                 state_dir=e.get("PS2_HANDICAP_STATE", "claude_bridge/handicap_state").strip(),
                 tag=tag)
        hc.load()
        return hc

    # ------------------------------------------------------------ rule
    def applies(self, slot):
        return slot in self.slots

    def update(self, won):
        w = 1.0 if won else 0.0
        self.ema += (w - self.ema) / self.window
        self.h = min(1.0, max(self.h_min, self.h - self.step * (w - self.target)))
        self.n += 1
        self.wins += int(w)
        self.save()

    # ------------------------------------------------------ carry-over
    def _path(self):
        return os.path.join(self.state_dir, f"hcap_i{self.tag}.json")

    def load(self):
        """Read the carry-over folder once; never raises."""
        if not self.state_dir:
            return
        try:
            files = glob.glob(os.path.join(self.state_dir, "hcap_i*.json"))
            rows = []
            for f in files:
                try:
                    d = json.load(open(f))
                    h, ema = float(d["h"]), float(d["ema"])
                    if not (0.0 < h <= 1.0 and 0.0 <= ema <= 1.0):
                        continue
                    rows.append((os.path.getmtime(f), h, ema))
                except Exception:
                    continue
            if not rows:
                return
            newest = max(r[0] for r in rows)
            rows = [r for r in rows if r[0] >= newest - HOURS_FRESH * 3600.0]
            self.h = min(1.0, max(self.h_min, sum(r[1] for r in rows) / len(rows)))
            self.ema = sum(r[2] for r in rows) / len(rows)
            self.carried = len(rows)
        except Exception:
            self.h, self.ema, self.carried = 1.0, self.target, 0

    def save(self):
        """Atomic write of this env's state; never raises (a full disk must not kill an actor)."""
        if not self.state_dir:
            return
        try:
            os.makedirs(self.state_dir, exist_ok=True)
            p = self._path()
            tmp = p + f".tmp{os.getpid()}"
            with open(tmp, "w") as f:
                json.dump({"h": round(self.h, 6), "ema": round(self.ema, 6), "n": self.n, "wins": self.wins,
                           "target": self.target, "min": self.h_min}, f)
            os.replace(tmp, p)
        except Exception:
            pass

    # ---------------------------------------------------------- logging
    def config_line(self):
        return (f"[config] handicap: learner health x h on slots {_fmt_slots(self.slots)}; target={self.target:g} "
                f"min={self.h_min:g} step={self.step:g} ema_window={self.window:g} start h={self.h:.3f} "
                f"ema={self.ema:.3f} (carried from {self.carried} file(s) in {self.state_dir or '-'})")

    def status_line(self):
        return (f"[hcap] i{self.tag} n={self.n} wins={self.wins} h={self.h:.3f} ema={self.ema:.3f} "
                f"target={self.target:g}")


def _fmt_slots(slots):
    s = sorted(slots)
    if not s:
        return "-"
    out, a, b = [], s[0], s[0]
    for x in s[1:]:
        if x == b + 1:
            b = x
            continue
        out.append(f"{a}-{b}" if b > a else f"{a}")
        a = b = x
    out.append(f"{a}-{b}" if b > a else f"{a}")
    return ",".join(out)
