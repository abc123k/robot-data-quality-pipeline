
import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class JointStateSimulator(Node):

    def __init__(self):
        super().__init__("joint_state_simulator")

        self.publisher = self.create_publisher(
            JointState,
            "/joint_states",
            10
        )

        self.joint_names = [
            "joint_1",
            "joint_2",
            "joint_3",
            "joint_4",
            "joint_5",
            "joint_6"
        ]

        self.start_time = self.get_clock().now()
        self.timer = self.create_timer(0.1, self.publish_joint_state)

        self.get_logger().info("JointState simulator started")

    def publish_joint_state(self):
        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds / 1e9

        msg = JointState()
        msg.header.stamp = now.to_msg()
        msg.name = self.joint_names

        # 模拟六个关节的位置
        msg.position = [
            0.5 * math.sin(elapsed + i * 0.3)
            for i in range(6)
        ]

        # 模拟六个关节的速度
        msg.velocity = [
            0.5 * math.cos(elapsed + i * 0.3)
            for i in range(6)
        ]

        # 模拟六个关节的力矩
        msg.effort = [
            2.0 * math.sin(elapsed + i * 0.2)
            for i in range(6)
        ]

        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = JointStateSimulator()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

