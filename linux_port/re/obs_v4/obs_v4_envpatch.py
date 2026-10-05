"""obs_v4_envpatch.py -- the INTEGRATION.md env change as a mixin (PROPOSAL; used by the tests and equivalence_v4.py,
and usable as-is if Blake prefers a subclass over editing powerstone_env_v6.py / ffa_selfplay_env.py).

    from obs_v4_envpatch import with_obs_v4
    Env = with_obs_v4(PowerStoneEnvLibretro)          # or FFASelfPlayEnv
    env = Env(core_path=..., ...)                      # obs is 430-dim; obs[:160] = the v3 builder, untouched

Semantics (identical to the INTEGRATION.md patch):
  * requires the obs-v3 line (PS2_OBS_V3=1) and a libretro env (RAM access via self._lr_bridge.ram);
  * obs[160:430] = ObsV4Reader.features(AGENT_PLAYER - 1, the v2 opponent order, self._lr_synth.frame);
    AGENT_PLAYER / _active_opp are swapped by FFASelfPlayEnv._obs_from_view, so every seat's view is right;
  * PS2_OBS_V4_ITEMEMB=zero (default) writes 0 into obs[12..17] unless self._legacy_item is set (a <=160-dim
    consumer: v2/v3 pool seat or eval of an older model), =keep leaves the slot-hash embedding in place;
  * the reader's clocks restart on every loadstate.
"""
import os

import numpy as np

import obs_v4_reader as V


def with_obs_v4(base):
    class ObsV4Env(base):
        OBS_DIM = V.V4_DIM
        OBS_V4_ITEMEMB = os.environ.get("PS2_OBS_V4_ITEMEMB", "zero")

        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            assert self.OBS_V3, "obs v4 needs the obs-v3 line (PS2_OBS_V3=1)"
            import gym
            self.observation_space = gym.spaces.Box(-5.0, 5.0, (V.V4_DIM,), np.float32)

        def _v4_reader(self):
            r = getattr(self, "_v4", None)
            if r is None:
                r = self._v4 = V.ObsV4Reader(self._lr_bridge.ram)
            return r

        def _send(self, cmd):
            super()._send(cmd)
            if cmd.startswith("loadstate"):
                self._v4_reader().reset()

        def _observe(self, s, prev):
            obs = super()._observe(s, prev)               # OBS_DIM-sized; the v3 builder fills [0..159]
            seat = self.AGENT_PLAYER - 1
            oo = [j for _, j, _ in self._opps(s)[:self.N_OPP]]
            obs[V.V3_DIM:V.V4_DIM], _ = self._v4_reader().features(seat, oo, self._lr_synth.frame)
            if self.OBS_V4_ITEMEMB == "zero" and not getattr(self, "_legacy_item", False):
                obs[12:18] = 0.0
            return obs

        def _obs_from_view(self, v):
            """FFASelfPlayEnv only: a <=160-dim pool policy keeps the slot-hash [12..17] it was trained on."""
            n = int(v.model.observation_space.shape[0]) if getattr(v, "model", None) is not None else V.V4_DIM
            saved = getattr(self, "_legacy_item", False)
            self._legacy_item = (n % V.V4_DIM != 0)
            try:
                return super()._obs_from_view(v)
            finally:
                self._legacy_item = saved

    ObsV4Env.__name__ = f"ObsV4_{base.__name__}"
    return ObsV4Env
