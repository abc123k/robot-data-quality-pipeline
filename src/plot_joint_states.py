
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt

from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


BASE_DIR = Path.home() / "robot_data_quality"
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

mcap_files = list(BASE_DIR.rglob("*.mcap"))

if not mcap_files:
    raise FileNotFoundError("没有找到 MCAP 文件")

mcap_file = max(mcap_files, key=lambda p: p.stat().st_mtime)

msg_cls = get_message("sensor_msgs/msg/JointState")

data = defaultdict(
    lambda: {
        "time": [],
        "position": [],
        "velocity": [],
        "effort": []
    }
)

first_timestamp = None

with open(mcap_file, "rb") as f:
    reader = make_reader(f)

    for schema, channel, message in reader.iter_messages():

        if channel.topic != "/joint_states":
            continue

        msg = deserialize_message(message.data, msg_cls)

        timestamp = message.log_time

        if first_timestamp is None:
            first_timestamp = timestamp

        elapsed = (timestamp - first_timestamp) / 1e9

        lengths = [
            len(msg.name),
            len(msg.position),
            len(msg.velocity),
            len(msg.effort)
        ]

        if len(set(lengths)) != 1:
            continue

        for i, name in enumerate(msg.name):
            data[name]["time"].append(elapsed)
            data[name]["position"].append(float(msg.position[i]))
            data[name]["velocity"].append(float(msg.velocity[i]))
            data[name]["effort"].append(float(msg.effort[i]))


if not data:
    raise RuntimeError("没有读取到有效的关节数据")


fig, axes = plt.subplots(
    3, 1,
    figsize=(14, 11),
    sharex=True
)

fields = [
    ("position", "Joint Position", "Position (rad)"),
    ("velocity", "Joint Velocity", "Velocity (rad/s)"),
    ("effort", "Joint Effort", "Effort (Nm)")
]

for ax, (field, title, ylabel) in zip(axes, fields):

    for joint_name, values in sorted(data.items()):

        ax.plot(
            values["time"],
            values[field],
            label=joint_name,
            linewidth=1
        )

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(ncol=3)

axes[-1].set_xlabel("Time (seconds)")

fig.suptitle(
    f"Robot Joint State Analysis\n{mcap_file.name}"
)

fig.tight_layout()

output_path = REPORT_DIR / "joint_timeseries.png"

fig.savefig(
    output_path,
    dpi=160,
    bbox_inches="tight"
)

print("MCAP:", mcap_file.name)
print("关节数量:", len(data))
print("图表已保存:", output_path)

plt.show()

