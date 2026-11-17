
import csv
import json
from pathlib import Path
from collections import defaultdict
from statistics import mean, median
import math

from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

BASE_DIR = Path.home() / "robot_data_quality"
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

mcap_files = list(BASE_DIR.rglob("*.mcap"))
mcap_file = max(mcap_files, key=lambda p: p.stat().st_mtime)

msg_cls = get_message("sensor_msgs/msg/JointState")

joint_data = defaultdict(
    lambda: {
        "position": [],
        "velocity": [],
        "effort": []
    }
)

timestamps = []
invalid_messages = 0
duplicate_timestamps = 0
previous_timestamp = None
backward_timestamps = 0
message_count = 0

with open(mcap_file, "rb") as f:
    reader = make_reader(f)

    for schema, channel, message in reader.iter_messages():
        if channel.topic != "/joint_states":
            continue

        msg = deserialize_message(message.data, msg_cls)
        message_count += 1

        ts = message.log_time
        timestamps.append(ts)

        if previous_timestamp is not None:
            if ts == previous_timestamp:
                duplicate_timestamps += 1
            elif ts < previous_timestamp:
                backward_timestamps += 1

        previous_timestamp = ts

        if not (
            len(msg.name) == len(msg.position)
            == len(msg.velocity) == len(msg.effort)
        ):
            invalid_messages += 1
            continue

        if len(set(msg.name)) != len(msg.name):
            invalid_messages += 1
            continue

        for i, name in enumerate(msg.name):
            values = {
                "position": msg.position[i],
                "velocity": msg.velocity[i],
                "effort": msg.effort[i]
            }

            for field, value in values.items():
                if math.isfinite(value):
                    joint_data[name][field].append(float(value))
                else:
                    invalid_messages += 1

# 时间间隔分析：只统计正向时间间隔
intervals = [
    (timestamps[i] - timestamps[i - 1]) / 1e9
    for i in range(1, len(timestamps))
    if timestamps[i] > timestamps[i - 1]
]

avg_interval = mean(intervals) if intervals else None
median_interval = median(intervals) if intervals else None

report = {
    "source_file": str(mcap_file),
    "topic": "/joint_states",
    "message_count": message_count,
    "joint_count": len(joint_data),
    "invalid_messages": invalid_messages,
    "duplicate_timestamps": duplicate_timestamps,
    "backward_timestamps": backward_timestamps,
    "average_frequency_hz": (
        round(1 / avg_interval, 4) if avg_interval else None
    ),
    "average_interval_sec": (
        round(avg_interval, 6) if avg_interval else None
    ),
    "median_interval_sec": (
        round(median_interval, 6) if median_interval else None
    ),
    "joints": {}
}

csv_path = REPORT_DIR / "joint_statistics.csv"

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "joint", "field", "samples",
        "min", "max", "mean"
    ])

    for name, fields in sorted(joint_data.items()):
        report["joints"][name] = {}

        for field, values in fields.items():
            if not values:
                continue

            stats = {
                "samples": len(values),
                "min": round(min(values), 6),
                "max": round(max(values), 6),
                "mean": round(mean(values), 6)
            }

            report["joints"][name][field] = stats

            writer.writerow([
                name,
                field,
                stats["samples"],
                stats["min"],
                stats["max"],
                stats["mean"]
            ])

json_path = REPORT_DIR / "joint_quality_report.json"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("报告生成成功！")
print("JSON:", json_path)
print("CSV:", csv_path)
print("消息数量:", message_count)
print("关节数量:", len(joint_data))
print("无效消息:", invalid_messages)
print("重复时间戳:", duplicate_timestamps)
print("时间戳倒退:", backward_timestamps)
print("平均频率:", report["average_frequency_hz"], "Hz")

