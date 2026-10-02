import argparse
from pathlib import Path
import json
import torch
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.env_checker import check_env
from warpdrive.env import FurutaEnv
from warpdrive.model import load_parameters, save_parameters
from warpdrive.task import OBSERVATION_CONTRACT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--params', default='config/reactor_params.yaml')
    parser.add_argument('--out', default='runs/policy')
    parser.add_argument('--steps', type=int, default=200_000)
    parser.add_argument('--seed', type=int, default=7)
    args = parser.parse_args()
    if args.steps < 1:
        parser.error('--steps must be positive')
    torch.set_num_threads(1)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    p = load_parameters(args.params)
    save_parameters(p, out/'reactor_params.yaml')
    (out/'contract.json').write_text(json.dumps({
        'observation': OBSERVATION_CONTRACT, 'action': 'current/current_limit',
        'algorithm': 'SAC', 'seed': args.seed, 'requested_steps': args.steps,
    }, indent=2))
    env = Monitor(FurutaEnv(p), str(out/'training'))
    check_env(env.unwrapped, warn=True)
    evaluation = Monitor(FurutaEnv(p))
    evaluation.reset(seed=10007)
    callback = EvalCallback(evaluation, best_model_save_path=str(out),
                            log_path=str(out), eval_freq=10_000,
                            n_eval_episodes=5, deterministic=True)
    model = SAC('MlpPolicy', env, learning_rate=3e-4, buffer_size=200_000,
                learning_starts=2_000, batch_size=256, gamma=0.99,
                tau=0.005, train_freq=1, gradient_steps=1,
                policy_kwargs={'net_arch': [64, 64]}, seed=args.seed,
                device='cpu', verbose=0)
    model.learn(total_timesteps=args.steps, callback=callback)
    model.save(out/'policy')
    env.close()
    evaluation.close()
    print(f'Saved {out}/policy.zip. Evaluate before calling this a successful controller.', flush=True)


if __name__ == '__main__':
    main()
