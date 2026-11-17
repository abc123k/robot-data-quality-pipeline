
from pathlib import Path
from collections import Counter
from statistics import median
import csv
import math

from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


# =========================
# 1. 基础配置
# =========================

BASE_DIR = Path.home() / "robot_data_quality"
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

mcap_files = list(BASE_DIR.rglob("*.mcap"))

if not mcap_files:
    raise FileNotFoundError("项目目录中没有找到 MCAP 文件")

mcap_file = max(mcap_files, key=lambda p: p.stat().st_mtime)

msg_cls = get_message("sensor_msgs/msg/JointState")

EXPECTED_JOINTS = {
    "joint_1", "joint_2", "joint_3",
    "joint_4", "joint_5", "joint_6"
}

# 以下均为当前模拟数据的教学实验阈值
POSITION_LIMIT = 0.55
VELOCITY_LIMIT = 0.60
EFFORT_LIMIT = 2.10
VELOCITY_JUMP_LIMIT = 0.25

# 模拟器目标发布频率为 10Hz
EXPECTED_INTERVAL = 0.1
GAP_LIMIT = EXPECTED_INTERVAL * 1.5


# =========================
# 2. 数据结构
# =========================

records = []
anomalies = []

def add_anomaly(timestamp, joint, field, value, reason, category):
    anomalies.append({
        "timestamp_ns": timestamp,
        "joint": joint,
        "field": field,
        "value": value,
        "reason": reason,
        "category": category
    })


# =========================
# 3. 读取和检查 MCAP
# =========================

with open(mcap_file, "rb") as f:
    reader = make_reader(f)

    for schema, channel, message in reader.iter_messages():

        if channel.topic != "/joint_states":
            continue

        timestamp = message.log_time

        try:
            msg = deserialize_message(message.data, msg_cls)
        except Exception as exc:
            add_anomaly(
                timestamp, "ALL", "message",
                str(exc), "消息反序列化失败", "完整性"
            )
            continue

        # 检查字段长度
        lengths = [
            len(msg.name),
            len(msg.position),
            len(msg.velocity),
            len(msg.effort)
        ]

        if len(set(lengths)) != 1:
            add_anomaly(
                timestamp, "ALL", "message",
                str(lengths), "字段长度不一致", "完整性"
            )
            continue

        # 检查关节名称重复
        if len(set(msg.name)) != len(msg.name):
            add_anomaly(
                timestamp, "ALL", "name",
                str(msg.name), "关节名称重复", "完整性"
            )
            continue

        actual_joints = set(msg.name)

        # 检查关节集合是否符合预期
        if actual_joints != EXPECTED_JOINTS:
            missing = sorted(EXPECTED_JOINTS - actual_joints)
            extra = sorted(actual_joints - EXPECTED_JOINTS)

            add_anomaly(
                timestamp, "ALL", "joint_names",
                f"missing={missing}; extra={extra}",
                "关节名称集合与预期不一致",
                "完整性"
            )

        record = {
            "timestamp": timestamp,
            "joints": {}
        }

        for i, name in enumerate(msg.name):

            values = {
                "position": float(msg.position[i]),
                "velocity": float(msg.velocity[i]),
                "effort": float(msg.effort[i])
            }

            record["joints"][name] = values

            limits = {
                "position": POSITION_LIMIT,
                "velocity": VELOCITY_LIMIT,
                "effort": EFFORT_LIMIT
            }

            for field, value in values.items():

                if not math.isfinite(value):
                    add_anomaly(
                        timestamp, name, field,
                        value, "NaN或Inf", "数值有效性"
                    )

                elif abs(value) > limits[field]:
                    add_anomaly(
                        timestamp, name, field,
                        value, "超过实验阈值", "数值范围"
                    )

        records.append(record)


# =========================
# 4. 时间戳和消息间隔检查
# =========================

intervals = []

for i in range(1, len(records)):

    previous = records[i - 1]["timestamp"]
    current = records[i]["timestamp"]

    if current == previous:
        add_anomaly(
            current, "ALL", "timestamp",
            current, "重复时间戳", "时间戳"
        )

    elif current < previous:
        add_anomaly(
            current, "ALL", "timestamp",
            current, "时间戳倒退", "时间戳"
        )

    else:
        gap = (current - previous) / 1e9
        intervals.append(gap)

        if gap > GAP_LIMIT:
            add_anomaly(
                current, "ALL", "interval",
                round(gap, 6), "消息间隔过长", "频率"
            )


# =========================
# 5. 速度突变检查
# =========================

for i in range(1, len(records)):

    previous = records[i - 1]["joints"]
    current = records[i]["joints"]
    timestamp = records[i]["timestamp"]

    for name in current:

        if name not in previous:
            continue

        old_velocity = previous[name]["velocity"]
        new_velocity = current[name]["velocity"]

        if (
            math.isfinite(old_velocity)
            and math.isfinite(new_velocity)
            and abs(new_velocity - old_velocity) > VELOCITY_JUMP_LIMIT
        ):
            add_anomaly(
                timestamp, name, "velocity",
                new_velocity, "速度突变", "运动连续性"
            )


# =========================
# 6. 生成 CSV 报告
# =========================

csv_path = REPORT_DIR / "anomaly_report.csv"

fieldnames = [
    "timestamp_ns",
    "joint",
    "field",
    "value",
    "reason",
    "category"
]

with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(anomalies)


# =========================
# 7. 输出统计结果
# =========================

print("========== 机器人数据异常检测 ==========")
print("文件:", mcap_file.name)
print("有效解析消息数量:", len(records))
print("异常总数量:", len(anomalies))
print("预期关节数量:", len(EXPECTED_JOINTS))

if intervals:
    print("消息间隔中位数:", round(median(intervals), 4), "秒")
    print("消息间隔异常阈值:", GAP_LIMIT, "秒")

print("\n========== 异常分类统计 ==========")

category_counts = Counter(
    item["category"] for item in anomalies
)

if category_counts:
    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count}")
else:
    print("没有检测到异常")

print("\n========== 异常详情 ==========")

for item in anomalies[:20]:
    print(
        item["category"],
        item["joint"],
        item["field"],
        item["value"],
        item["reason"]
    )

if len(anomalies) > 20:
    print("其余异常请查看 CSV 文件")

print("\n报告已保存:", csv_path)

