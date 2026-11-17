
from pathlib import Path

from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

# MCAP 数据目录
DATA_DIR = Path.home() / "robot_data_quality" / "data"
mcap_files = list(DATA_DIR.glob("*.mcap"))

if not mcap_files:
    raise FileNotFoundError("没有找到 MCAP 文件")

mcap_file = mcap_files[0]

# 当前测试 Bag 中 /chatter 的消息类型
topic_types = {
    "/chatter": "std_msgs/msg/String"
}

print("========== ROS 2 MCAP 解码 ==========")
print("文件:", mcap_file.name)

message_classes = {}
decoded_count = {}

with open(mcap_file, "rb") as f:
    reader = make_reader(f)

    for schema, channel, message in reader.iter_messages():
        topic = channel.topic

        # 优先使用 MCAP Schema 中的消息类型
        msg_type = schema.name if schema and schema.name else topic_types.get(topic)

        if not msg_type:
            print("跳过未知消息类型:", topic)
            continue

        if msg_type not in message_classes:
            message_classes[msg_type] = get_message(msg_type)

        # 二进制 CDR 数据解码为 ROS 2 消息对象
        msg = deserialize_message(
            message.data,
            message_classes[msg_type]
        )

        decoded_count[topic] = decoded_count.get(topic, 0) + 1

        # 展示前 5 条消息
        if decoded_count[topic] <= 5:
            print(f"\nTopic: {topic}")
            print("消息类型:", msg_type)
            print("解码结果:", msg)

            if hasattr(msg, "data"):
                print("实际字符串内容:", msg.data)

print("\n========== 解码统计 ==========")

for topic, count in decoded_count.items():
    print(f"{topic}: 成功解码 {count} 条消息")

