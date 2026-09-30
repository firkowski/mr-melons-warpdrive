"""Complete the callback, then run this file after sourcing ROS 2 Humble."""
import rclpy
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
        super().__init__('reactor_policy')
        torch.set_num_threads(1)

        # TODO: Declare a node parameter 'model_file' that stores the path to the .zip policy saved in `runs/policy/`
        # path = ...

        # TODO: Declare a node parameter 'parameters_file' that stores the .yaml file with the system parameters
        #       you obtained previously
        # config = ...
        # self.p = load_parameters(config)

        # Load the policy
        self.policy = SAC.load(path, device='cpu')

        # TODO: Create a servo current publisher that publishes a message of type Float64 to '/reactor/current_cmd'
        #       What QoS would be the best for a controller? 
        # self.publisher = ...
        
        # TODO: Subscribe to the topic '/joint_states' with message type JointState and callback function self.on_state

    # The callback function that runs anytime the node receives `joint_states` from the simulator node
    def on_state(self, msg):
        pass
        # TODO: Convert the JointState message into the physical state [theta, alpha, theta_dot, alpha_dot].
        #       Look the joints up by name; do not assume the message order.
        #       Hint: use the state_from_joint_state() helper function
        # state = ...

        # TODO: Build the policy input. The policy expects exactly what FurutaEnv.step() returned
        #       during training, which is not the raw state. Check warpdrive/env.py to see how
        #       that input is built, and reuse the same helper instead of rebuilding it by hand.
        # obs = ...

        # TODO: Infer the normalized action by running policy.predict(..., deterministic=True)
        #       on the policy input from the previous step
        # action, _ = ...

        # TODO: Convert normalized action from the policy ([-1, 1]) to Amperes
        # current = ...

        # TODO: Publish current value using the previously created publisher


def main():
    rclpy.init()
    node = PolicyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
