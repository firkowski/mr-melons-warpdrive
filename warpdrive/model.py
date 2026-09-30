"""Two rigid bodies, ideal current control, diagonal pendulum COM inertia.

Coordinates: Rz(theta) Rx(alpha), pendulum COM at (0, 0, l) in its frame.
alpha=0 is upright; positive alpha tips towards negative local y.
"""
from dataclasses import asdict, dataclass, fields
from pathlib import Path
import math
import numpy as np
import yaml


@dataclass(frozen=True)
class Parameters:
    arm_length: float
    arm_inertia: float
    pendulum_mass: float
    pendulum_com: float
    pendulum_ixx: float
    pendulum_iyy: float
    pendulum_izz: float
    arm_damping: float
    pendulum_damping: float
    torque_constant: float
    current_limit: float
    gravity: float
    control_dt: float
    physics_substeps: int
    episode_seconds: float
    arm_speed_limit: float
    pendulum_speed_limit: float

    def __post_init__(self):
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f'{f.name} must be a finite number')
            if v < 0 or (v == 0 and not f.name.endswith('_damping')):
                raise ValueError(f'{f.name} must be positive (damping may be zero)')
        if not isinstance(self.physics_substeps, int):
            raise ValueError('physics_substeps must be an integer')
        inertias = [self.pendulum_ixx, self.pendulum_iyy, self.pendulum_izz]
        if 2 * max(inertias) > sum(inertias) + 1e-12:
            raise ValueError('Pendulum inertia violates the triangle inequality')
        n = self.episode_seconds / self.control_dt
        if not math.isclose(n, round(n)):
            raise ValueError('episode_seconds must be an integer multiple of control_dt')


def load_parameters(path):
    if not path:
        raise ValueError('No parameters_file given; pass the YAML from config/ or runs/policy/')
    data = yaml.safe_load(Path(path).read_text())
    expected = {f.name for f in fields(Parameters)}
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError('Parameter YAML must contain exactly the documented parameter keys')
    return Parameters(**data)


def save_parameters(p, path):
    Path(path).write_text(yaml.safe_dump(asdict(p), sort_keys=False))


def mass_matrix(alpha, p):
    s, c = math.sin(alpha), math.cos(alpha)
    ml2 = p.pendulum_mass * p.pendulum_com ** 2
    coupling = p.pendulum_mass * p.arm_length * p.pendulum_com
    return np.array([
        [p.arm_inertia + p.pendulum_mass * p.arm_length ** 2
         + (p.pendulum_iyy + ml2) * s*s + p.pendulum_izz * c*c,
         -coupling * c],
        [-coupling * c, p.pendulum_ixx + ml2],
    ])


def derivative(state, current, p):
    _, alpha, td, ad = state
    s, c = math.sin(alpha), math.cos(alpha)
    ml2 = p.pendulum_mass * p.pendulum_com ** 2
    k = p.pendulum_mass * p.arm_length * p.pendulum_com
    d = p.pendulum_iyy + ml2 - p.pendulum_izz
    m11 = p.arm_inertia + p.pendulum_mass * p.arm_length**2 + p.pendulum_izz + d*s*s
    m12 = -k*c
    m22 = p.pendulum_ixx + ml2
    torque = p.torque_constant * max(-p.current_limit, min(p.current_limit, current))
    b1 = torque - p.arm_damping*td - 2*d*s*c*td*ad - k*s*ad*ad
    b2 = p.pendulum_mass*p.gravity*p.pendulum_com*s - p.pendulum_damping*ad + d*s*c*td*td
    det = m11*m22 - m12*m12
    return np.array([td, ad, (m22*b1-m12*b2)/det, (m11*b2-m12*b1)/det])


def step_dynamics(state, current, p):
    """Hold current for one control interval; fixed-step RK4 in both runtimes."""
    x = np.asarray(state, dtype=np.float64).copy()
    if x.shape != (4,) or not np.isfinite(x).all() or not math.isfinite(current):
        raise ValueError('Expected a finite four-element state and finite current')
    h = p.control_dt / p.physics_substeps
    for _ in range(p.physics_substeps):
        k1 = derivative(x, current, p)
        k2 = derivative(x+h*k1/2, current, p)
        k3 = derivative(x+h*k2/2, current, p)
        k4 = derivative(x+h*k3, current, p)
        x += h*(k1+2*k2+2*k3+k4)/6
        if not np.isfinite(x).all():
            raise FloatingPointError('Dynamics became non-finite')
    return x


def energy(state, p):
    v = np.asarray(state[2:])
    return float(0.5*v @ mass_matrix(state[1], p) @ v
                 + p.pendulum_mass*p.gravity*p.pendulum_com*math.cos(state[1]))
