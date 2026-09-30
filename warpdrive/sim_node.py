"""ROS 2 wrapper for the same integrator used by Gymnasium."""
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from std_srvs.srv import Trigger
from .model import load_parameters, step_dynamics
from .task import JOINT_NAMES, failure, initial_state


class Simulator(Node):
    def __init__(self):
        super().__init__('warpdrive_simulator')
        path = self.declare_parameter('parameters_file', '').value
        self.p = load_parameters(path or None)
        seed = self.declare_parameter('seed', 7).value
        self.rng = np.random.default_rng(seed)
        self.state = initial_state(self.rng)
        self.current = 0.0
        self.last_command = None
        self.paused = False
        qos = QoSProfile(depth=1)
        self.publisher = self.create_publisher(JointState, '/joint_states', qos)
        self.create_subscription(Float64, '/reactor/current_cmd', self.command, qos)
        self.create_service(Trigger, '/reactor/reset', self.reset)
        self.create_timer(self.p.control_dt, self.tick)
        self.get_logger().info('Current commands in A; alpha=0 upright. Reset: /reactor/reset.')

    def command(self, msg):
        if not np.isfinite(msg.data):
            self.current, self.last_command = 0.0, None
            self.get_logger().warning('Rejected non-finite current command')
            return
        self.current = float(np.clip(msg.data, -self.p.current_limit, self.p.current_limit))
        self.last_command = time.monotonic()

    def reset(self, request, response):
        self.state = initial_state(self.rng)
        self.current, self.last_command, self.paused = 0.0, None, False
        response.success = True
        response.message = 'Reactor reset to hanging down.'
        return response

    def tick(self):
        # Zero-order hold. Drop commands if the policy stops publishing.
        fresh = self.last_command is not None and time.monotonic()-self.last_command < 0.1
        if not self.paused:
            try:
                next_state = step_dynamics(self.state, self.current if fresh else 0.0, self.p)
                if failure(next_state, self.p):
                    raise FloatingPointError('Speed limit exceeded')
                self.state = next_state
            except (FloatingPointError, OverflowError, ValueError) as exc:
                self.paused, self.current = True, 0.0
                self.get_logger().error(f'{exc}; paused. Use /reactor/reset.')
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(JOINT_NAMES)
        msg.position = self.state[:2].tolist()
        msg.velocity = self.state[2:].tolist()
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = Simulator()
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
