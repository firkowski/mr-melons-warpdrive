# Mr. Melon’s Warpdrive - student package

Read `ASSIGNMENT.md` first for the tasks and grading. This file covers setup and the commands
for each step. The assignment website shows the same steps with commands for macOS, Windows and
Ubuntu side by side.

Before asking a TA or an AI tool for help, read the AI & TA policy at the end of `ASSIGNMENT.md`:
ask about the system, not the solution.

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

On every operating system we use **ROS 2 Humble from RoboStack**, installed with micromamba into
an environment called `ros_env`. RoboStack brings its own Python, so ROS, training and the policy
node all use the same interpreter. Use a terminal (macOS, Ubuntu) or **PowerShell** (Windows)
for every command.

### 1.1 Install micromamba

macOS and Ubuntu:

```sh
"${SHELL}" <(curl -L micro.mamba.pm/install.sh)
```

(On macOS, `brew install micromamba` also works.)

Windows (PowerShell):

```powershell
Invoke-Expression ((Invoke-WebRequest -Uri https://micro.mamba.pm/install.ps1 -UseBasicParsing).Content)
```

Windows also needs **Visual Studio 2022 with C++ support** (“Desktop development with C++”).
Close and reopen the terminal afterwards.

### 1.2 Create the ROS 2 environment

The same on all systems:

```sh
micromamba create -n ros_env -c conda-forge -c robostack-humble ros-humble-desktop
micromamba activate ros_env
micromamba config append channels robostack-humble --env
micromamba install -c conda-forge ros-dev-tools git
rviz2
```

If an RViz window opens, ROS works. Activating `ros_env` also sets up ROS; never source a
system ROS installation on top of it. See the
[RoboStack guide](https://robostack.github.io/micromamba.html) if something fails.

### 1.3 Get the package and install the Python dependencies

Go to the folder where you want to keep your work; the workspace is created there. Choose a path
without spaces, and avoid folders synced by OneDrive or iCloud.

macOS and Ubuntu:

```sh
mkdir -p reactor_ws/src && cd reactor_ws/src
git clone https://github.com/firkowski/mr-melons-warpdrive.git melon_warpdrive
cd melon_warpdrive
```

Windows (use a short path without spaces, for example directly in `C:\`):

```powershell
mkdir reactor_ws\src; cd reactor_ws\src
git clone https://github.com/firkowski/mr-melons-warpdrive.git melon_warpdrive
cd melon_warpdrive
```

Then, with `ros_env` active, install PyTorch (CPU) and the package’s dependencies:

```sh
# macOS
python -m pip install torch
# Ubuntu and Windows
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu

# all systems
python -m pip install -e ".[rl,plots]" "setuptools<80"
```

`setuptools<80` avoids a colcon error (`option --editable not recognized`).

### 1.4 Build the workspace

Go from the package folder up to the workspace folder (`cd ../..`; Windows: `cd ..\..`) and note
its full path, printed by `pwd` (Windows: `Get-Location`). You need it in every new terminal.

macOS and Ubuntu, from the workspace folder:

```sh
colcon build --symlink-install --packages-select melon_warpdrive
source install/setup.zsh     # macOS (zsh); on Ubuntu: source install/setup.bash
```

Windows, from the workspace folder. Turn on **Developer Mode** in the Windows settings first; it allows
the symlinks that `--symlink-install` creates.

```powershell
colcon build --symlink-install --merge-install --packages-select melon_warpdrive
.\install\setup.ps1
```

`--symlink-install` means edits to Python files, the URDF and the YAML take effect without
rebuilding. **Rebuild** after adding new files, such as `pendulum.stl`: run the same `colcon build`
command from the workspace folder, then `cd src/melon_warpdrive` back into the package.

### Every new terminal

Replace `path/to/reactor_ws` with the workspace path you noted when building.

```sh
micromamba activate ros_env
cd path/to/reactor_ws              # Windows: cd path\to\reactor_ws
source install/setup.zsh           # macOS; Ubuntu: source install/setup.bash; Windows: .\install\setup.ps1
cd src/melon_warpdrive             # Windows: cd src\melon_warpdrive
```

All commands below are the same on every system.

### Check the installation

From the package folder, start the simulator and RViz with the approximate parameters that come
with the dummy policy:

```sh
ros2 launch melon_warpdrive reactor.launch.py "parameters_file:=$PWD/runs/dummy/reactor_params.yaml"
```

RViz should open and show the reactor with a glitched-out pendulum at the tip of the arm. The glitch
is intended: you replace the mesh with your own model in Part 1. Stop the launch with Ctrl+C.

## 2. CAD values and visual model

`urdf/model/pendulum.stl` is a glitched-out placeholder, so you can test the ROS loop before your
CAD model is finished. Replace it with your own export.

1. Fill in the five `null` values in `config/reactor_params.yaml`.
2. Check that the file loads:

   ```sh
   python -c "from warpdrive.model import load_parameters; print(load_parameters('config/reactor_params.yaml'))"
   ```

3. Export `urdf/model/pendulum.stl`, set the pendulum’s visual origin in `urdf/reactor.urdf`, and
   rebuild the workspace.
4. Check the result in RViz without a controller:

   ```sh
   ros2 launch melon_warpdrive reactor.launch.py "parameters_file:=$PWD/config/reactor_params.yaml"
   ```

   Your pendulum (not the glitched placeholder) should hang from the arm tip and swing about its pivot.

## 3. Test the ROS loop with a dummy policy

The package includes a safe dummy policy, `runs/dummy/policy.zip`: a policy with the
correct input and output sizes. It turns the arm at about 1 rad/s and does not swing the pendulum up, so
you can see in RViz that your node's commands reach the simulator. The commands below use your completed `config/reactor_params.yaml`. If you have not finished Part 1
yet, you can use the approximate `runs/dummy/reactor_params.yaml` instead; switch to your own values
before you train.

Use three terminals, each set up as in “Every new terminal”.

Terminal 1, simulator, `robot_state_publisher` and RViz:

```sh
ros2 launch melon_warpdrive reactor.launch.py "parameters_file:=$PWD/config/reactor_params.yaml"
```

Terminal 2, your policy node:

```sh
ros2 run melon_warpdrive controller --ros-args -p "model_file:=$PWD/runs/dummy/policy.zip" -p "parameters_file:=$PWD/config/reactor_params.yaml"
```

Terminal 3, reset the reactor:

```sh
ros2 service call /reactor/reset std_srvs/srv/Trigger "{}"
```

Then inspect the commands. `ros2 topic echo` and `ros2 topic hz` keep running until you stop them
with Ctrl+C, so run them one after the other, or each in its own terminal:

```sh
ros2 topic echo /reactor/current_cmd
```

```sh
ros2 topic hz /reactor/current_cmd
```

Run only one policy node at a time. The simulator applies zero current if it receives no command
for 100 ms. To test the simulator without a policy, publish a constant current at 50 Hz (values
beyond `current_limit` are clipped):

```sh
ros2 topic pub -r 50 /reactor/current_cmd std_msgs/msg/Float64 "{data: 0.1}"
```

Larger currents spin the arm up until it exceeds its speed limit (at 1 A after about 8 s); the
simulator then pauses until you call `/reactor/reset`.

## 4. Reward, training and evaluation

Training and evaluation run without ROS. Implement `reward()` in `warpdrive/task.py`, then train:

```sh
python -m warpdrive.train --out runs/policy --seed 7
```

Defaults: `--params config/reactor_params.yaml --out runs/policy --steps 200000 --seed 7`.
Training 200,000 steps takes about 10–20 minutes on a recent laptop CPU (longer in a virtual machine). It writes to `runs/policy/`:

| File | Content |
|---|---|
| `policy.zip` | policy at the end of training |
| `best_model.zip` | best policy found by the periodic evaluation during training |
| `reactor_params.yaml` | copy of the exact parameters used; use this copy for everything below |
| `contract.json` | observation/action definition, seed and step count |
| `evaluations.npz`, `training.monitor.csv` | learning curves |

`best_model.zip` and `evaluations.npz` are first written at the periodic evaluation after 10,000
steps; a shorter test run only writes `policy.zip`, so use that file in the commands below.

Use a different `--out` folder for each run you want to keep (and `--steps N` to change the training length). Watch a trained policy in RViz with
the commands from step 3, pointing `model_file` and `parameters_file` at `runs/policy/`.

Evaluate the policy and the zero-current baseline on the fixed evaluation seeds:

```sh
python -m warpdrive.evaluate --model runs/policy/best_model.zip --params runs/policy/reactor_params.yaml --out runs/policy/evaluation
python -m warpdrive.evaluate --params runs/policy/reactor_params.yaml --out runs/zero_current
```

Each writes `metrics.json` (success rate and per-episode results) and `trajectory.csv` (first
episode). An episode counts as a success if no speed limit was exceeded and the pendulum is
balanced (`upright(state)`) at every control sample of the final three seconds. Plot a trajectory:

```sh
python tools/plot_trace.py runs/policy/evaluation/trajectory.csv --out runs/policy/evaluation/trajectory.png
python tools/plot_trace.py runs/zero_current/trajectory.csv --out runs/zero_current/trajectory.png
```

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `micromamba: command not found` | The installer changed your shell profile. Close and reopen the terminal. |
| `ros2: command not found` / `ModuleNotFoundError: rclpy` | `ros_env` is not active. Run `micromamba activate ros_env`. |
| `Package 'melon_warpdrive' not found` | The workspace is not sourced in this terminal, or not built. Build, then source `install/setup.*`. |
| `ValueError: pendulum_mass must be a finite number` | A value in the parameter file is still `null`. Pass a complete file with `parameters_file:=...`. |
| `No parameters_file given` | The node or script was started without a parameter file. |
| `FileNotFoundError: runs/policy/...` | Relative paths are resolved from the current folder. Run from the package folder and pass `$PWD/...` paths. |
| `NotImplementedError: Task 2.1: ...` from the policy node | A TODO in `warpdrive/policy_node.py` is not finished yet; the message says which part. |
| Policy node runs without errors, but `ros2 topic hz /reactor/current_cmd` shows nothing | The current message is built but never published. Check `PolicyNode.publish_current`. |
| Simulator log: `Speed limit exceeded; paused` | The arm or pendulum spun too fast. Call `/reactor/reset`. |
| RViz still shows the glitched placeholder pendulum | Your export is not at `urdf/model/pendulum.stl` or has a different file name. Save it there (in mm), rebuild and re-source. |
| `colcon build`: `option --editable not recognized` | setuptools is too new for colcon: `python -m pip install "setuptools<80"`. |
| Windows: `colcon build` fails creating symlinks | Turn on Developer Mode, or build without `--symlink-install` and rebuild after every edit. |
| Windows: `setup.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. |
| Nodes do not see each other (`ros2 topic list` misses topics) | Allow network access when the firewall asks, or set `ROS_LOCALHOST_ONLY=1` in every terminal (`export ROS_LOCALHOST_ONLY=1`; PowerShell: `$env:ROS_LOCALHOST_ONLY=1`). |

See `docs/DYNAMICS.md` for the frame conventions, equations and CAD unit conversions.
The package contains no hardware motor driver: the assignment deploys into simulation.
