
from pathlib import Path
from collections import defaultdict
from statistics import mean, median
import math

from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

BASE_DIR = Path.home() / "robot_data_quality"

# 找到最近录制的 MCAP 文件
mcap_files = list(BASE_DIR.rglob("*.mcap"))

if not mcap_files:
    raise FileNotFoundError("没有找到 MCAP 文件")

mcap_file = max(mcap_files, key=lambda p: p.stat().st_mtime)

print("========== 关节数据解码 ==========")
print("MCAP 文件:", mcap_file)

topic_types = {
    "/joint_states": "sensor_msgs/msg/JointState"
}

msg_classes = {}
joint_data = defaultdict(
    lambda: {
        "position": [],
        "velocity": [],
        "effort": []
    }
)

message_count = 0
invalid_count = 0
timestamps = []
joint_names_seen = set()

with open(mcap_file, "rb") as f:
    reader = make_reader(f)

    for schema, channel, message in reader.iter_messages():
        topic = channel.topic

        if topic != "/joint_states":
            continue

        msg_type = topic_types.get(topic)

        if msg_type not in msg_classes:
            msg_classes[msg_type] = get_message(msg_type)

        msg = deserialize_message(
            message.data,
            msg_classes[msg_type]
        )

        message_count += 1
        timestamps.append(message.log_time)

        if message_count <= 3:
            print(f"\n第 {message_count} 条消息")
            print("关节名称:", msg.name)
            print("位置:", msg.position)
            print("速度:", msg.velocity)
            print("力矩:", msg.effort)

        # 检查各字段长度
        if not (
            len(msg.name) == len(msg.position)
            and len(msg.name) == len(msg.velocity)
            and len(msg.name) == len(msg.effort)
        ):
            invalid_count += 1
            continue

        for i, name in enumerate(msg.name):
            joint_names_seen.add(name)

            for field in ["position", "velocity", "effort"]:
                value = getattr(msg, field)[i]

                if math.isfinite(value):
                    joint_data[name][field].append(value)
                else:
                    invalid_count += 1

print("\n========== 数据质量报告 ==========")
print("成功解码消息数:", message_count)
print("发现的关节数量:", len(joint_names_seen))
print("字段异常计数:", invalid_count)

if len(timestamps) > 1:
    intervals = [
        (timestamps[i] - timestamps[i - 1]) / 1e9
        for i in range(1, len(timestamps))
    ]

    print("平均消息间隔:", round(mean(intervals), 4), "秒")
    print("中位消息间隔:", round(median(intervals), 4), "秒")
    print("平均发布频率:", round(1 / mean(intervals), 2), "Hz")

print("\n========== 各关节数据统计 ==========")

for name in sorted(joint_names_seen):
    print(f"\n关节: {name}")

    for field in ["position", "velocity", "effort"]:
        values = joint_data[name][field]

        if values:
            print(
                f"{field}: "
                f"min={min(values):.4f}, "
                f"max={max(values):.4f}, "
                f"mean={mean(values):.4f}, "
                f"samples={len(values)}"
            )
        else:
            print(f"{field}: 无有效数据")

