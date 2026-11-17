
from mcap.reader import make_reader
from pathlib import Path

bag_dir = Path.home() / "robot_data_quality" / "data"
mcap_file = next(bag_dir.glob("*.mcap"))

topic_info = {}

with open(mcap_file, "rb") as f:
    reader = make_reader(f)

    for schema, channel, message in reader.iter_messages():
        topic = channel.topic

        if topic not in topic_info:
            topic_info[topic] = {
                "message_type": schema.name if schema else "未知",
                "schema_encoding": schema.encoding if schema else "未知",
                "message_encoding": channel.message_encoding,
                "sample_size": len(message.data),
                "sample_data": message.data[:50]
            }

print("========== MCAP 消息类型检查 ==========")

for topic, info in topic_info.items():
    print(f"\nTopic: {topic}")
    print("消息类型:", info["message_type"])
    print("Schema 编码:", info["schema_encoding"])
    print("消息编码:", info["message_encoding"])
    print("样本大小:", info["sample_size"], "bytes")
    print("原始数据片段:", info["sample_data"])

