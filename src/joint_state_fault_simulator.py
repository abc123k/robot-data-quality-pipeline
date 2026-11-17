
import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class FaultSimulator(Node):

    def __init__(self):
        super().__init__("joint_state_fault_simulator")

        self.publisher = self.create_publisher(
            JointState, "/joint_states", 10
        )

        self.joint_names = [
            "joint_1", "joint_2", "joint_3",
            "joint_4", "joint_5", "joint_6"
        ]

        self.start_time = self.get_clock().now()
        self.counter = 0
        self.timer = self.create_timer(0.1, self.publish_data)

        self.get_logger().info("Fault simulator started")

    def publish_data(self):
        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds / 1e9

        msg = JointState()
        msg.header.stamp = now.to_msg()
        msg.name = self.joint_names

        positions = [
            0.5 * math.sin(elapsed + i * 0.3)
            for i in range(6)
        ]

        msg.velocity = [
            0.5 * math.cos(elapsed + i * 0.3)
            for i in range(6)
        ]

        msg.effort = [
            2.0 * math.sin(elapsed + i * 0.2)
            for i in range(6)
        ]

        self.counter += 1

                # 故障2：制造错误的关节名称
        if self.counter == 70:
            msg.name = list(self.joint_names)
            msg.name[5] = "joint_extra"
            self.get_logger().warning(
                "Injected fault: joint_6 renamed to joint_extra"
            )

        # 故障3：制造 NaN 数值
        if self.counter == 80:
            positions[0] = float("nan")
            self.get_logger().warning(
                "Injected fault: joint_1 position = NaN"
            )

        # 人为制造一次位置异常
        if self.counter == 50:
            positions[2] = 0.8
            self.get_logger().warning(
                "Injected fault: joint_3 position = 0.8"
            )

        msg.position = positions
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = FaultSimulator()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

