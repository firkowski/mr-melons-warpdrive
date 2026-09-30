"""Common, seed-controlled assessment. Works with the student and solution policies."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from .env import FurutaEnv
from .model import load_parameters


def evaluate(predict, p, episodes=20, seed=20000):
    env = FurutaEnv(p)
    results, trace = [], []
    hold_steps = round(3.0/p.control_dt)
    for episode in range(episodes):
        obs, _ = env.reset(seed=seed+episode)
        total, streak, longest, first_hold = 0.0, 0, 0, None
        up_flags = []
        for step in range(env.max_steps):
            action = predict(obs)
            obs, r, terminated, truncated, info = env.step(action)
            total += r
            streak = streak+1 if info['upright'] else 0
            longest = max(longest, streak)
            up_flags.append(info['upright'])
            if streak >= hold_steps and first_hold is None:
                first_hold = (step+1-hold_steps)*p.control_dt
            if episode == 0:
                trace.append([(step+1)*p.control_dt, *info['state'], info['current'], r])
            if terminated or truncated:
                break
        success = bool(not terminated and streak >= hold_steps)
        results.append({'seed': seed+episode, 'success': success,
                        'return': total, 'duration_s': (step+1)*p.control_dt,
                        'longest_hold_s': longest*p.control_dt,
                        'first_three_second_hold_start_s': first_hold,
                        'final_three_second_upright_fraction':
                            sum(up_flags[-hold_steps:])/hold_steps,
                        'terminated': terminated})
    env.close()
    return {'episodes': results, 'success_rate': float(np.mean([r['success'] for r in results])),
            'mean_return': float(np.mean([r['return'] for r in results]))}, trace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='SAC checkpoint; omit for zero-current baseline')
    parser.add_argument('--params', default='config/reactor_params.yaml')
    parser.add_argument('--episodes', type=int, default=20)
    parser.add_argument('--seed', type=int, default=20000)
    parser.add_argument('--out', default='runs/evaluation')
    args = parser.parse_args()
    if args.episodes < 1:
        parser.error('--episodes must be positive')
    if args.model:
        import torch
        from stable_baselines3 import SAC
        torch.set_num_threads(1)
        model = SAC.load(args.model, device='cpu')
        predict = lambda obs: model.predict(obs, deterministic=True)[0]
    else:
        predict = lambda obs: np.zeros(1, dtype=np.float32)
    report, trace = evaluate(predict, load_parameters(args.params), args.episodes, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out/'metrics.json').write_text(json.dumps(report, indent=2))
    with (out/'trajectory.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time_s','theta_rad','alpha_rad','theta_dot_rad_s','alpha_dot_rad_s','current_A','reward'])
        writer.writerows(trace)
    print(json.dumps({k:v for k,v in report.items() if k != 'episodes'}, indent=2))


if __name__ == '__main__':
    main()
