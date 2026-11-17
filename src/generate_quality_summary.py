
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict


ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports"

MANIFEST = REPORT_DIR / "dataset_manifest.csv"


def to_int(value):
    return int(value) if value not in ("", None) else 0


def to_float(value):
    return float(value) if value not in ("", None) else None


def main():
    if not MANIFEST.exists():
        raise FileNotFoundError(
            f"找不到数据集清单: {MANIFEST}"
        )

    with open(MANIFEST, newline="", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    if not records:
        raise RuntimeError("数据集清单为空")

    category_stats = defaultdict(
        lambda: {"file_count": 0, "message_count": 0}
    )

    status_counts = Counter()
    issue_file_counts = Counter()

    total_messages = 0
    anomaly_records = []

    for record in records:
        category = record["category"]
        status = record["quality_status"]
        message_count = to_int(record["message_count"])

        category_stats[category]["file_count"] += 1
        category_stats[category]["message_count"] += message_count

        status_counts[status] += 1
        total_messages += message_count

        issues = [
            issue.strip()
            for issue in record.get("issues", "").split(";")
            if issue.strip()
        ]

        if status == "ANOMALY_DETECTED":
            for issue in issues:
                issue_file_counts[issue] += 1

            anomaly_records.append({
                "file": record["file"],
                "category": category,
                "message_count": message_count,
                "quality_status": status,
                "joint_count": record["joint_count"],
                "nan_inf_count": record["nan_inf_count"],
                "field_length_errors": record["field_length_errors"],
                "position_limit_errors": record["position_limit_errors"],
                "interval_errors": record["interval_errors"],
                "duplicate_name_errors": record["duplicate_name_errors"],
                "interval_max": record["interval_max"],
                "issues": record["issues"],
            })

    summary = {
        "total_files": len(records),
        "total_messages": total_messages,
        "category_statistics": dict(category_stats),
        "quality_status_counts": dict(status_counts),
        "anomaly_files": len(anomaly_records),
        "anomaly_issue_file_counts": dict(issue_file_counts),
        "notes": [
            "异常类型数量表示包含该异常的文件数，不代表异常事件总次数。",
            "PASS仅表示通过当前实验检测规则。",
            "NOT_APPLICABLE表示该文件不属于JointState关节数据。",
        ],
    }

    json_path = REPORT_DIR / "quality_summary.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    csv_path = REPORT_DIR / "anomaly_summary.csv"

    fields = [
        "file",
        "category",
        "message_count",
        "quality_status",
        "joint_count",
        "nan_inf_count",
        "field_length_errors",
        "position_limit_errors",
        "interval_errors",
        "duplicate_name_errors",
        "interval_max",
        "issues",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(anomaly_records)

    print("\n========== 数据集质量汇总 ==========")
    print("总文件数:", summary["total_files"])
    print("总消息数:", summary["total_messages"])
    print("异常文件数:", summary["anomaly_files"])

    print("\n各类别统计:")
    for category, stats in category_stats.items():
        print(
            f"  {category}: "
            f"{stats['file_count']} files, "
            f"{stats['message_count']} messages"
        )

    print("\n质量状态统计:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    print("\n异常类型统计（按文件数）:")
    for issue, count in issue_file_counts.items():
        print(f"  {issue}: {count} 个文件")

    print("\n报告已生成:")
    print(json_path)
    print(csv_path)


if __name__ == "__main__":
    main()

