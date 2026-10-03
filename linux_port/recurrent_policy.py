"""recurrent_policy.py — memory for the Power Stone 2 bot (Oct 2 2026, 9950X; HANDOFF NEXT MOVES #4).

SkipLSTMPolicy: sb3-contrib's RecurrentActorCriticPolicy with two changes, both so a leg-N MLP policy can
be warm-started EXACTLY (the frame-stack "surgery" pattern, not distillation):
  1. SKIP: the MLP heads read [features, lstm_out] instead of lstm_out alone. Surgery copies the parent's
     first-layer weights into the feature columns and ZEROS the lstm columns, so at step 0 the recurrent
     policy is the parent bit for bit; memory enters only as training moves those weights off zero.
  2. NARROW LSTM INPUT: the LSTM reads only the newest frame (the last `lstm_input_dim` features, 160
     under obs v3), not the whole K=7 stack: the stack still covers the last 1.6 s, the LSTM carries what
     is older. PokeRL (Oct 1 sidebar) used a 128-unit LSTM; that is the default here.

Policy-agnostic helpers used by the trainer, evaluators and pool seats:
  is_recurrent_zip(path)     True if the zip was saved by RecurrentPPO
  load_model(path)           PPO or RecurrentPPO, CPU
  PolicyRunner(model)        .reset() at every episode start, .act(obs, deterministic) per step
"""
import json
import zipfile

import numpy as np
import torch as th
from sb3_contrib.common.recurrent.policies import RecurrentActorCriticPolicy
from stable_baselines3.common.torch_layers import MlpExtractor

CUSTOM_OBJECTS = {"clip_range": 0.2, "lr_schedule": lambda _: 2.5e-4}


class SkipLSTMPolicy(RecurrentActorCriticPolicy):
    def __init__(self, *args, lstm_input_dim=None, **kwargs):
        self.lstm_input_dim = lstm_input_dim
        super().__init__(*args, **kwargs)
        if lstm_input_dim is not None and lstm_input_dim != self.features_dim:
            # rebuild both LSTMs on the narrow input, then the optimizer over the final parameters
            hid = self.lstm_output_dim
            nl = self.lstm_actor.num_layers
            self.lstm_actor = th.nn.LSTM(lstm_input_dim, hid, num_layers=nl, **self.lstm_kwargs)
            if self.lstm_critic is not None:
                self.lstm_critic = th.nn.LSTM(lstm_input_dim, hid, num_layers=nl, **self.lstm_kwargs)
            self.optimizer = self.optimizer_class(self.parameters(), lr=self._lr0, **self.optimizer_kwargs)

    def _build(self, lr_schedule):
        self._lr0 = lr_schedule(1)
        super()._build(lr_schedule)

    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MlpExtractor(
            self.features_dim + self.lstm_output_dim,      # SKIP: [features, lstm_out]
            net_arch=self.net_arch,
            activation_fn=self.activation_fn,
            device=self.device,
        )

    def _process_sequence(self, features, lstm_states, episode_starts, lstm):
        x = features[:, -lstm.input_size:]                  # newest frame only (or all, if same width)
        out, states = RecurrentActorCriticPolicy._process_sequence(x, lstm_states, episode_starts, lstm)
        return th.cat([features, out], dim=1), states

    def _get_constructor_parameters(self):
        data = super()._get_constructor_parameters()
        data["lstm_input_dim"] = self.lstm_input_dim
        return data


def is_recurrent_zip(path):
    p = path if path.endswith(".zip") else path + ".zip"
    with zipfile.ZipFile(p) as z:
        data = json.loads(z.read("data").decode())
    pc = json.dumps(data.get("policy_class", ""))
    return "Recurrent" in pc or "SkipLSTM" in pc


def load_model(path, **kwargs):
    p = path.removesuffix(".zip")
    kw = dict(device="cpu", custom_objects=CUSTOM_OBJECTS)
    kw.update(kwargs)
    if is_recurrent_zip(p):
        from sb3_contrib import RecurrentPPO
        m = RecurrentPPO.load(p, **kw)
    else:
        from stable_baselines3 import PPO
        m = PPO.load(p, **kw)
    # Oct 3 2026 BUG FIX: SB3's load() re-seeds python/numpy/torch from the zip's stored seed. surgery_lstm.py saved
    # seed=0, so every process loading a recurrent zip (all 20 eval shards, all 16 actors) started from the SAME random
    # state: the shards replayed identical rounds (legs 110-111 lv8mix = 50 distinct rounds x 20) and the actors drew
    # correlated episodes. Drop the stored seed and re-seed every generator from fresh entropy.
    if getattr(m, "seed", None) is not None:
        import random as _random
        m.seed = None
        _random.seed()
        np.random.seed(None)
        th.seed()
    return m


class PolicyRunner:
    """Steps any policy one observation at a time. Feedforward models ignore the state; recurrent ones
    keep their LSTM state between act() calls and zero it on reset() (call at every episode start)."""

    def __init__(self, model):
        self.model = model
        self.recurrent = isinstance(model.policy, RecurrentActorCriticPolicy)
        self.reset()

    def reset(self):
        self.state = None
        self.start = np.ones((1,), dtype=bool)

    def act(self, obs, deterministic=False):
        if not self.recurrent:
            a, _ = self.model.predict(obs, deterministic=deterministic)
            return a
        a, self.state = self.model.predict(obs, state=self.state, episode_start=self.start,
                                           deterministic=deterministic)
        self.start = np.zeros((1,), dtype=bool)
        return a
