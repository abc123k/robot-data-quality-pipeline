
import csv
import json
import math
from pathlib import Path
from collections import defaultdict
from statistics import median

from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"

CATEGORIES = ["normal", "fault_injection", "raw"]
EXPECTED_JOINTS = {f"joint_{i}" for i in range(1, 7)}

JOINT_STATE_TYPE = "sensor_msgs/msg/JointState"
POSITION_LIMIT = 0.55
INTERVAL_LIMIT = 0.15


def analyze_file(path, category):
    print(f"Analyzing: {path.name}")

    result = {
        "file": path.name,
        "category": category,
        "file_size_bytes": path.stat().st_size,
        "message_count": 0,
        "topics": set(),
        "message_types": {},
        "joint_count": 0,
        "joint_names": set(),
        "interval_median": None,
        "interval_max": None,
        "nan_inf_count": 0,
        "field_length_errors": 0,
        "position_limit_errors": 0,
        "interval_errors": 0,
        "duplicate_name_errors": 0,
        "quality_status": "NOT_APPLICABLE",
        "issues": [],
    }

    timestamps = []
    issues = []

    msg_class = get_message(JOINT_STATE_TYPE)

    with open(path, "rb") as f:
        reader = make_reader(f)

        for schema, channel, message in reader.iter_messages():
            result["message_count"] += 1
            result["topics"].add(channel.topic)

            if schema:
                result["message_types"][channel.topic] = schema.name

            if channel.topic != "/joint_states":
                continue

            msg = deserialize_message(message.data, msg_class)
            timestamps.append(message.log_time)

            if not (
                len(msg.name) == len(msg.position)
                == len(msg.velocity) == len(msg.effort)
            ):
                result["field_length_errors"] += 1
                continue

            if len(set(msg.name)) != len(msg.name):
                result["duplicate_name_errors"] += 1

            result["joint_names"].update(msg.name)

            for value in msg.position:
                if not math.isfinite(value):
                    result["nan_inf_count"] += 1
                elif abs(value) > POSITION_LIMIT:
                    result["position_limit_errors"] += 1

            for field in ("velocity", "effort"):
                for value in getattr(msg, field):
                    if not math.isfinite(value):
                        result["nan_inf_count"] += 1

    result["topics"] = sorted(result["topics"])
    result["joint_names"] = sorted(result["joint_names"])
    result["joint_count"] = len(result["joint_names"])

    if len(timestamps) > 1:
        intervals = [
            (timestamps[i] - timestamps[i - 1]) / 1e9
            for i in range(1, len(timestamps))
        ]

        result["interval_median"] = median(intervals)
        result["interval_max"] = max(intervals)

        result["interval_errors"] = sum(
            interval > INTERVAL_LIMIT or interval <= 0
            for interval in intervals
        )

    if category != "raw":
        if result["joint_names"] != sorted(EXPECTED_JOINTS):
            issues.append("关节名称集合与预期不一致")

        if result["nan_inf_count"]:
            issues.append("存在NaN或Inf")

        if result["field_length_errors"]:
            issues.append("存在字段长度异常")

        if result["position_limit_errors"]:
            issues.append("存在位置越界")

        if result["interval_errors"]:
            issues.append("存在时间间隔异常")

        if result["duplicate_name_errors"]:
            issues.append("存在重复关节名称")

        result["quality_status"] = (
            "ANOMALY_DETECTED" if issues else "PASS"
        )

    result["issues"] = issues

    # CSV/JSON友好格式
    result["message_types"] = json.dumps(
        result["message_types"], ensure_ascii=False
    )
    result["topics"] = ";".join(result["topics"])
    result["joint_names"] = ";".join(result["joint_names"])
    result["issues"] = ";".join(result["issues"])

    return result


def main():
    REPORT_DIR.mkdir(exist_ok=True)

    records = []

    for category in CATEGORIES:
        folder = DATA_DIR / category

        for path in sorted(folder.glob("*.mcap")):
            try:
                records.append(analyze_file(path, category))
            except Exception as exc:
                print(f"ERROR: {path.name}: {exc}")

    if not records:
        raise RuntimeError("没有成功分析任何 MCAP 文件")

    fields = list(records[0].keys())

    csv_path = REPORT_DIR / "dataset_manifest.csv"
    json_path = REPORT_DIR / "dataset_manifest.json"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print("\n========== 数据集清单完成 ==========")
    print("成功分析文件数:", len(records))

    for record in records:
        print(
            record["category"],
            record["file"],
            "messages =", record["message_count"],
            "status =", record["quality_status"],
            "issues =", record["issues"] or "无",
        )

    print("\nCSV:", csv_path)
    print("JSON:", json_path)


if __name__ == "__main__":
    main()

