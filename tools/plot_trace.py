"""Plot the supplied evaluator's CSV. Optional install: pip install -e '.[plots]'."""
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('trajectory')
    parser.add_argument('--out', default='trajectory.png')
    args = parser.parse_args()
    d = np.genfromtxt(args.trajectory, delimiter=',', names=True)
    t = d['time_s']
    alpha = np.degrees(np.arctan2(np.sin(d['alpha_rad']), np.cos(d['alpha_rad'])))
    alpha[np.flatnonzero(np.abs(np.diff(alpha)) > 180)+1] = np.nan
    fig, ax = plt.subplots(3, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
    fig.suptitle('Mr. Melon’s reactor — learned swing-up and balancing', fontsize=15)
    ax[0].plot(t, alpha, color='#c56716', linewidth=1.5)
    ax[0].axhspan(-10, 10, color='#27916a', alpha=0.12, label='Balance angle band: ±10°')
    ax[0].set_ylabel('Wrapped pendulum angle (°)')
    ax[0].set_ylim(-190, 190)
    ax[0].legend(loc='upper right')
    ax[1].plot(t, d['theta_dot_rad_s'], label='Arm', color='#2667a0')
    ax[1].plot(t, d['alpha_dot_rad_s'], label='Pendulum', color='#c56716')
    ax[1].set_ylabel('Angular speed (rad/s)')
    ax[1].legend(loc='upper right')
    ax[2].plot(t, d['current_A'], color='#2667a0')
    ax[2].set_ylabel('Current (A)')
    ax[2].set_xlabel('Time (s)')
    for a in ax:
        a.axvspan(max(0,t[-1]-3), t[-1], color='#27916a', alpha=0.07)
        a.grid(alpha=0.2)
        a.set_xlim(0, t[-1])
    ax[0].text(0.71, 0.08, 'Final 3 s: assessment window', transform=ax[0].transAxes, fontsize=9)
    ax[0].text(0.01, 0.06, '0° = upright; ±180° = hanging down', transform=ax[0].transAxes, fontsize=9)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170)
    fig.savefig(out.with_suffix('.svg'))
    plt.close(fig)


if __name__ == '__main__':
    main()
