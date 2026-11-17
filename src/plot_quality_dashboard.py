
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports"

with open(REPORT_DIR / "quality_summary.json", encoding="utf-8") as f:
    summary = json.load(f)

with open(REPORT_DIR / "dataset_manifest.csv",
          newline="", encoding="utf-8") as f:
    records = list(csv.DictReader(f))


# 1. 质量状态统计
status_counts = summary["quality_status_counts"]

# 2. 各类别消息数量
category_stats = summary["category_statistics"]
categories = list(category_stats.keys())
message_counts = [
    category_stats[name]["message_count"]
    for name in categories
]

# 3. 异常类型统计
issue_counts = summary["anomaly_issue_file_counts"]
issue_labels = {
    "存在位置越界": "Position limit",
    "存在时间间隔异常": "Timing interval",
    "关节名称集合与预期不一致": "Joint name mismatch",
    "存在NaN或Inf": "NaN / Inf",
    "存在字段长度异常": "Field length",
    "存在重复关节名称": "Duplicate joint name",
}
issue_names = [
    issue_labels.get(name, name)
    for name in issue_counts
]
issue_values = list(issue_counts.values())

# 4. 每份JointState数据的最大消息间隔
joint_records = [
    r for r in records
    if r["joint_count"] not in ("", "0")
]

file_labels = [
    r["file"].replace("rosbag2_2026_11_17-", "").replace("_0.mcap", "")
    for r in joint_records
]
interval_max = [
    float(r["interval_max"])
    for r in joint_records
    if r["interval_max"]
]


fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle(
    "Robot Data Quality Dashboard",
    fontsize=18,
    fontweight="bold"
)

# 左上：质量状态
ax = axes[0, 0]
labels = list(status_counts.keys())
values = list(status_counts.values())

ax.bar(labels, values)
ax.set_title("Quality Status")
ax.set_ylabel("Number of files")
ax.tick_params(axis="x", rotation=15)

for i, value in enumerate(values):
    ax.text(i, value + 0.05, str(value), ha="center")


# 右上：数据类别消息数量
ax = axes[0, 1]
ax.bar(categories, message_counts)
ax.set_title("Messages by Dataset Category")
ax.set_ylabel("Number of messages")

for i, value in enumerate(message_counts):
    ax.text(i, value, f"{value:,}", ha="center", va="bottom")


# 左下：异常类型
ax = axes[1, 0]
ax.barh(issue_names, issue_values)
ax.set_title("Anomaly Types (File Count)")
ax.set_xlabel("Number of files")

for i, value in enumerate(issue_values):
    ax.text(value + 0.03, i, str(value), va="center")


# 右下：最大消息间隔
ax = axes[1, 1]
ax.bar(file_labels, interval_max)
ax.axhline(
    y=0.15,
    linestyle="--",
    label="Interval threshold (0.15s)"
)
ax.set_title("Maximum Message Interval")
ax.set_ylabel("Seconds")
ax.tick_params(axis="x", rotation=25)
ax.legend()


fig.text(
    0.5,
    0.015,
    f"Files: {summary['total_files']} | "
    f"Messages: {summary['total_messages']:,} | "
    f"Anomaly files: {summary['anomaly_files']}",
    ha="center",
    fontsize=11
)

plt.tight_layout(rect=[0, 0.04, 1, 0.94])

output = REPORT_DIR / "quality_dashboard.png"
plt.savefig(output, dpi=180, bbox_inches="tight")

print("Dashboard generated:", output)
print("Total files:", summary["total_files"])
print("Total messages:", summary["total_messages"])
print("Anomaly files:", summary["anomaly_files"])

plt.show()

