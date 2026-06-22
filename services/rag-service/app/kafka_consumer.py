import json
from kafka import KafkaConsumer

def start_consumer(topic: str):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers="kafka:9092",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="rag-service-group",
    )

    for msg in consumer:
        print(f"[rag-service] received:", msg.value)
