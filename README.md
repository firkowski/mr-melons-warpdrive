# Mr. Melon’s Warpdrive — student package

Read `ASSIGNMENT.md` first for the tasks and grading. This file covers setup and the commands
for each step.

The package lives in a colcon workspace:

```
reactor_ws/
└── src/
    └── melon_warpdrive/     ← this folder; run all commands below from here unless stated
```

## What you edit

| File | What to do |
|---|---|
| `config/reactor_params.yaml` | Replace the `null` pendulum values with your CAD results |
| `urdf/model/pendulum.stl` | Your exported pendulum mesh (in mm) |
| `urdf/reactor.urdf` | Set the pendulum’s visual `<origin>` (marked TODO) |
| `warpdrive/task.py` | Implement `reward()` |
| `warpdrive/policy_node.py` | Complete the ROS policy node (marked TODO) |

Everything else is supplied. Do not change the physics (`model.py`), the environment (`env.py`),
the simulator or the evaluator.

## 1. Setup

Choose **one** of the two options. Both use ROS 2 Humble.

### Option A: RoboStack (micromamba) — Linux, macOS, Windows

Install ROS 2 Humble with micromamba by following the
[RoboStack guide](https://robostack.github.io/micromamba.html), including the tools for local
development (colcon). Then, inside the activated environment:

```sh
micromamba activate ros_env
cd reactor_ws/src/melon_warpdrive
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[rl,plots]'
```

In this option, `python` below means the environment’s Python, and ROS is already sourced when
the environment is active.

### Option B: Ubuntu 22.04 with ROS 2 Humble from apt

Install ROS 2 Humble Desktop and `python3-colcon-common-extensions` following the official ROS
instructions. ROS uses the system Python 3.10, and `ros2 run` starts the policy node with it, so
install the Python dependencies for that interpreter:

```sh
source /opt/ros/humble/setup.bash
cd reactor_ws/src/melon_warpdrive
python3 -m pip install --user torch --index-url https://download.pytorch.org/whl/cpu
python3 -m pip install --user -e '.[rl,plots]' "numpy<2"
```

`numpy<2` keeps NumPy compatible with the ROS packages from apt. In this option, use `python3`
wherever the commands below say `python`, and source ROS in every new terminal:
`source /opt/ros/humble/setup.bash`.

### Build the workspace

From `reactor_ws/`:

```sh
colcon build --symlink-install --packages-select melon_warpdrive
source install/setup.bash        # or install/setup.zsh in zsh
```

`--symlink-install` means edits to Python files, the URDF and the YAML take effect without
rebuilding. **Rebuild** after adding new files, such as `pendulum.stl`. Source
`install/setup.bash` in every new terminal that uses `ros2`.

## 2. CAD values and visual model

1. Fill in the five `null` values in `config/reactor_params.yaml`.
2. Check that the file loads:

   ```sh
   python -c "from warpdrive.model import load_parameters; print(load_parameters('config/reactor_params.yaml'))"
   ```

3. Export `urdf/model/pendulum.stl`, set the pendulum’s visual origin in `urdf/reactor.urdf`, and
   rebuild the workspace.
4. Check the result in RViz (see step 4 below): with no controller running, the pendulum should
   hang from the arm tip and swing about its pivot.

## 3. Reward, training and evaluation

Training and evaluation run without ROS.

Implement `reward()` in `warpdrive/task.py`, then train:

```sh
python -m warpdrive.train
```

Defaults: `--params config/reactor_params.yaml --out runs/policy --steps 200000 --seed 7`.
Training 200,000 steps can take 20–60 minutes on a laptop CPU. It writes to `runs/policy/`:

| File | Content |
|---|---|
| `policy.zip` | policy at the end of training |
| `best_model.zip` | best policy found by the periodic evaluation during training |
| `parameters.yaml` | exact parameters used; use this file for everything below |
| `contract.json` | observation/action definition, seed and step count |
| `evaluations.npz`, `training.monitor.csv` | learning curves |

Use a different `--out` folder for each run you want to keep.

Evaluate the policy and the zero-current baseline on the fixed evaluation seeds:

```sh
python -m warpdrive.evaluate --model runs/policy/best_model.zip --params runs/policy/parameters.yaml --out runs/policy/evaluation
python -m warpdrive.evaluate --params runs/policy/parameters.yaml --out runs/zero_current
```

Each writes `metrics.json` (success rate and per-episode results) and `trajectory.csv` (first
episode). Plot a trajectory:

```sh
python tools/plot_trace.py runs/policy/evaluation/trajectory.csv --out runs/policy/evaluation/trajectory.png
```

## 4. Run the ROS loop

Use three terminals, each with ROS and `reactor_ws/install/setup.bash` sourced, and each in this
folder so `$PWD` expands to the right path.

Terminal 1: simulator, `robot_state_publisher` and RViz:

```sh
ros2 launch melon_warpdrive reactor.launch.py parameters_file:=$PWD/runs/policy/parameters.yaml
```

Terminal 2: your policy node:

```sh
ros2 run melon_warpdrive controller --ros-args \
  -p model_file:=$PWD/runs/policy/best_model.zip \
  -p parameters_file:=$PWD/runs/policy/parameters.yaml
```

Terminal 3: reset the reactor to start a swing-up, and inspect the commands:

```sh
ros2 service call /reactor/reset std_srvs/srv/Trigger '{}'
ros2 topic echo /reactor/current_cmd
```

Run only one policy node at a time. The simulator applies zero current if it receives no command
for 100 ms.

To test the simulator without a policy, publish a constant current at 50 Hz (values beyond
`current_limit` are clipped):

```sh
ros2 topic pub -r 50 /reactor/current_cmd std_msgs/msg/Float64 '{data: 1.0}'
```

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ValueError: pendulum_mass must be a finite number` | A value in the parameter file is still `null`. Pass a complete file with `parameters_file:=...`. |
| `No parameters_file given` | The node or script was started without a parameter file. |
| `FileNotFoundError: runs/policy/...` | Relative paths are resolved from the current folder. Pass absolute paths, e.g. with `$PWD`. |
| `NotImplementedError` or `NameError` in the policy node | The TODOs in `warpdrive/policy_node.py` are not finished yet. |
| Simulator log: `Speed limit exceeded; paused` | The arm or pendulum spun too fast. Call `/reactor/reset`. |
| Pendulum mesh missing in RViz | `pendulum.stl` was added after the last build. Rebuild and re-source. |
| `colcon build`: `option --editable not recognized` | Your setuptools is too new for colcon: `python -m pip install "setuptools<80"`. |
| `ModuleNotFoundError: stable_baselines3` from `ros2 run` | The Python that runs ROS does not have the RL packages. Install them for that interpreter (see Setup). |

See `docs/DYNAMICS.md` for the frame conventions, equations and CAD unit conversions.
The package contains no hardware motor driver: the assignment deploys into simulation.
