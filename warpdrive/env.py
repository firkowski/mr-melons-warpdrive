import gymnasium as gym
import numpy as np
from .model import load_parameters, step_dynamics
from .task import action_to_current, failure, initial_state, observation, reward, upright


class FurutaEnv(gym.Env):
    metadata = {'render_modes': []}

    def __init__(self, parameters=None):
        self.p = parameters or load_parameters(None)
        self.action_space = gym.spaces.Box(-1, 1, (1,), np.float32)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (6,), np.float32)
        self.max_steps = round(self.p.episode_seconds/self.p.control_dt)
        self.state = None
        self.steps = 0
        self.done = True

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.state = initial_state(self.np_random)
        if options is not None and 'state' in options:
            x = np.asarray(options['state'], dtype=float)
            if x.shape != (4,) or failure(x, self.p):
                raise ValueError('Invalid reset state')
            self.state = x.copy()
        self.steps, self.done = 0, False
        return observation(self.state), {'state': self.state.copy()}

    def step(self, action):
        if self.done:
            raise RuntimeError('Call reset() before stepping a new episode')
        current = action_to_current(action, self.p)
        self.state = step_dynamics(self.state, current, self.p)
        self.steps += 1
        terminated = bool(failure(self.state, self.p))
        truncated = bool(self.steps >= self.max_steps and not terminated)
        self.done = terminated or truncated
        r = -10.0 if terminated else reward(self.state, current/self.p.current_limit)
        info = {'state': self.state.copy(), 'current': current, 'upright': upright(self.state)}
        return observation(self.state), r, terminated, truncated, info
