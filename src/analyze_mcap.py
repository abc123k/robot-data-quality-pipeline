
import csv
import json
from pathlib import Path
from collections import defaultdict
from statistics import median

# 项目路径
BASE_DIR = Path.home() / "robot_data_quality"
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

mcap_files = list(DATA_DIR.glob("*.mcap"))

if not mcap_files:
    raise FileNotFoundError(f"没有找到 MCAP 文件：{DATA_DIR}")

# 按 Topic 收集数据
topic_data = defaultdict(lambda: {
    "timestamps": [],
    "message_count": 0,
    "payload_bytes": 0
})

from mcap.reader import make_reader

for mcap_file in mcap_files:
    print(f"正在分析：{mcap_file.name}")

    with open(mcap_file, "rb") as f:
        reader = make_reader(f)

        for schema, channel, message in reader.iter_messages():
            topic = channel.topic
            item = topic_data[topic]

            item["message_count"] += 1
            item["payload_bytes"] += len(message.data)
            item["timestamps"].append(message.log_time)

# 生成分析报告
topic_reports = []

for topic, item in topic_data.items():
    timestamps = item["timestamps"]
    count = item["message_count"]

    sorted_times = sorted(timestamps)

    intervals = [
        (sorted_times[i] - sorted_times[i - 1]) / 1e9
        for i in range(1, len(sorted_times))
    ]

    duration = (
        (sorted_times[-1] - sorted_times[0]) / 1e9
        if len(sorted_times) > 1 else 0
    )

    avg_frequency = (
        (count - 1) / duration
        if duration > 0 else 0
    )

    duplicate_count = count - len(set(timestamps))

    if intervals:
        baseline = median(intervals)
        warning_threshold = baseline * 1.3
        critical_threshold = baseline * 2

        warning_count = sum(
            1 for x in intervals
            if warning_threshold < x <= critical_threshold
        )

        critical_count = sum(
            1 for x in intervals
            if x > critical_threshold
        )

        max_interval = max(intervals)
        median_interval = baseline
    else:
        warning_count = 0
        critical_count = 0
        max_interval = 0
        median_interval = 0

    topic_reports.append({
        "topic": topic,
        "message_count": count,
        "payload_bytes": item["payload_bytes"],
        "duration_sec": round(duration, 6),
        "avg_frequency_hz": round(avg_frequency, 3),
        "median_interval_ms": round(median_interval * 1000, 3),
        "max_interval_ms": round(max_interval * 1000, 3),
        "duplicate_timestamp_count": duplicate_count,
        "warning_gap_count": warning_count,
        "critical_gap_count": critical_count
    })

# 保存 JSON 报告
json_report = {
    "analyzed_files": [p.name for p in mcap_files],
    "topic_count": len(topic_reports),
    "total_messages": sum(
        x["message_count"] for x in topic_reports
    ),
    "topics": topic_reports
}

json_path = REPORT_DIR / "quality_report.json"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(json_report, f, ensure_ascii=False, indent=2)

# 保存 CSV 报告
csv_path = REPORT_DIR / "topic_statistics.csv"

if topic_reports:
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=topic_reports[0].keys()
        )
        writer.writeheader()
        writer.writerows(topic_reports)

# 输出摘要
print("\n========== 数据质量报告 ==========")
print("分析文件数量：", len(mcap_files))
print("Topic 数量：", len(topic_reports))
print("消息总数：", json_report["total_messages"])

for report in topic_reports:
    print(f"\nTopic: {report['topic']}")
    print("消息数量：", report["message_count"])
    print("平均频率：", report["avg_frequency_hz"], "Hz")
    print("重复时间戳：", report["duplicate_timestamp_count"])
    print("可疑间隔：", report["warning_gap_count"])
    print("严重间隔：", report["critical_gap_count"])

print("\n报告已生成：")
print(json_path)
print(csv_path)

