import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from stable_baselines3 import SAC
from warpdrive.model import load_parameters
from warpdrive.task import action_to_current, observation, state_from_joint_state

import torch


class PolicyNode(Node):
    def __init__(self):
        super().__init__('warpdrive_policy')
        torch.set_num_threads(1)

        # TODO: Declare a node parameter 'model_file' that stores the path to the .zip policy saved in `runs/policy/`
        path = None  # replace with your parameter

        # TODO: Declare a node parameter 'parameters_file' that stores the .yaml file with the system parameters
        #       (for a trained policy, the reactor_params.yaml copy saved next to it in `runs/policy/`;
        #       for the dummy policy, your completed `config/reactor_params.yaml`, or the approximate
        #       `runs/dummy/reactor_params.yaml` before you have finished Part 1)
        config = None  # replace with your parameter
        if path is None or config is None:
            raise NotImplementedError("Task 2.1: declare the 'model_file' and 'parameters_file' node parameters "
                                      "in PolicyNode.__init__ (see the TODOs in warpdrive/policy_node.py)")
        if not path or not config:
            raise ValueError("Pass both node parameters, for example: --ros-args "
                             "-p \"model_file:=$PWD/runs/policy/policy.zip\" "
                             "-p \"parameters_file:=$PWD/runs/policy/reactor_params.yaml\"")
        self.p = load_parameters(config)

        # Load the policy
        self.policy = SAC.load(path, device='cpu')
        if self.policy.observation_space.shape != (6,) or self.policy.action_space.shape != (1,):
            raise ValueError('The policy must use the supplied observation and action definition')

        # TODO: Create a servo current publisher that publishes a message of type Float64 to '/reactor/current_cmd'
        #       Hint: Use a RELIABLE QoS publisher with "QoSProfile(depth=1)"; the simulator subscribes with the same QoS
        self.publisher = None  # replace with your publisher

        # TODO: Subscribe to the topic '/joint_states' with message type JointState and callback function self.on_state
        #       Hint: use a QoS compatible with the simulator's publisher (it publishes with QoSProfile(depth=1))
        self.subscription = None  # replace with your subscription

        if self.publisher is None or self.subscription is None:
            raise NotImplementedError("Task 2.1: create the '/reactor/current_cmd' publisher and the '/joint_states' "
                                      "subscription in PolicyNode.__init__")

    def publish_current(self, value):
        """Publish one motor current command, in amperes."""
        # TODO: Create a Float64 message whose data is the current `value` in amperes, as a Python float,
        #       and publish it with the publisher you created in __init__
        msg = None  # replace with your message
        if msg is None:
            raise NotImplementedError("Task 2.1: build and publish the Float64 message in PolicyNode.publish_current")

    # The callback function that runs anytime the node receives `joint_states` from the simulator node
    def on_state(self, msg):
        # TODO: Convert the JointState message into the physical state [theta, alpha, theta_dot, alpha_dot].
        #       Look the joints up by name; do not assume the message order.
        #       Hint: use the state_from_joint_state() helper function. It raises ValueError or IndexError
        #       if the message is incomplete or contains non-finite values. Call it inside a try/except
        #       block; in the except branch, publish zero current with self.publish_current(0.0) and return.
        state = None  # replace with your state

        # TODO: Build the policy input. The policy expects exactly what FurutaEnv.step() returned
        #       during training, which is not the raw state. Check warpdrive/env.py to see how
        #       that input is built, and reuse the same helper instead of rebuilding it by hand.
        obs = None  # replace with your policy input

        # TODO: Infer the normalized action by running policy.predict(..., deterministic=True)
        #       on the policy input from the previous step
        action = None  # replace with your action

        # TODO: Convert normalized action from the policy ([-1, 1]) to Amperes
        current = None  # replace with your current

        missing = [name for name, value in (('state', state), ('obs', obs), ('action', action),
                                            ('current', current)) if value is None]
        if missing:
            raise NotImplementedError(f"Task 2.1: PolicyNode.on_state is not finished yet: {', '.join(missing)} "
                                      "(see the TODOs in warpdrive/policy_node.py)")
        self.publish_current(current)


def main():
    rclpy.init()
    node = PolicyNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            node.publish_current(0.0)  # best effort; the simulator also applies zero current after 100 ms
        except Exception:
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
