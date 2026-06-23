# import asyncio
# from collections.abc import Callable, Awaitable, Coroutine
# from typing import Any
# import json
# import logging
# from collections import defaultdict
# from aiokafka import (
#     AIOKafkaConsumer,
#     AIOKafkaProducer,
#     ConsumerRecord,
#     TopicPartition,
#     OffsetAndMetadata,
# )
# from rag_packages.shared.kafka.rebalancer import RebalanceListener
# from app.core.config import settings
# from app.consumers import user_consumers
# from app.kafka_producer import get_producer


# logger = logging.getLogger(__name__)
# service_name = settings.APP_NAME

# # "user.created.dlq": user_consumers.handle_user_created,
# # "user.updated.dlq": user_consumers.handle_user_updated,
# # "user.deleted.dlq": user_consumers.handle_user_deleted,

# HIGH_WATERMARK = 9990
# LOW_WATERMARK = 9000
# QUEUE_MAXSIZE = 10000

# TOPICS = [
#     "user.created",
#     "user.updated",
#     "user.deleted",
# ]

# HANDLERS = {
#     "user.created": user_consumers.handle_user_created,
#     "user.updated": user_consumers.handle_user_updated,
#     "user.deleted": user_consumers.handle_user_deleted,
# }

# consumer = None

# partition_queues: dict[TopicPartition, asyncio.Queue[ConsumerRecord]] = defaultdict(
#     lambda: asyncio.Queue(maxsize=QUEUE_MAXSIZE)
# )
# partition_tasks: dict[TopicPartition, asyncio.Task] = {}
# paused_partitions: set[TopicPartition] = set()


# def handle_partition_backpressure(partition: TopicPartition, service_name: str = "Service"):
#     # ? partition_queues is a defaultdict, so it will create a new queue if the partition doesn't exist
#     queue = partition_queues.get(partition)
#     if queue is None:
#         paused_partitions.discard(partition)
#         return

#     if queue.qsize() > HIGH_WATERMARK and partition not in paused_partitions:
#         logger.warning(
#             f"[{service_name}] partition {partition} queue size {queue.qsize()} exceeds high watermark {HIGH_WATERMARK}. Pausing consumption."
#         )
#         consumer.pause(partition)
#         paused_partitions.add(partition)

#     elif queue.qsize() < LOW_WATERMARK and partition in paused_partitions:
#         logger.info(
#             f"[{service_name}] partition {partition} queue size {queue.qsize()} below low watermark {LOW_WATERMARK}. Resuming consumption."
#         )
#         consumer.resume(partition)
#         paused_partitions.remove(partition)


# async def drain_partition_queue(
#     partition: TopicPartition,
#     # queue: asyncio.Queue[ConsumerRecord],
#     # handle_message: Callable[[ConsumerRecord], Awaitable[None]],
#     # handle_message: Callable[[ConsumerRecord], Coroutine[Any, Any, Any]],
#     # service_name: str = "Service",
# ):
#     queue = partition_queues.get(partition)
#     if queue is None:
#         paused_partitions.discard(partition)
#         return

#     while not queue.empty():
#         msg = await queue.get()
#         try:
#             await handle_message(msg)
#         except Exception as e:
#             logger.error(
#                 f"[{service_name}] error in partition worker during shutdown for partition {partition}: {e}"
#             )
#         finally:
#             queue.task_done()


# def get_consumer():
#     global consumer
#     if consumer is None:
#         consumer = AIOKafkaConsumer(
#             *TOPICS,
#             bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
#             value_deserializer=lambda m: json.loads(m.decode("utf-8")),
#             auto_offset_reset="earliest",
#             # enable_auto_commit=False,
#             group_id=service_name,
#         )

#         listener = RebalanceListener(
#             consumer,
#             partition_queues,
#             partition_tasks,
#             partition_worker=partition_worker,
#         )

#         consumer.subscribe(topics=TOPICS, listener=listener)
#     return consumer


# async def send_to_dlq(producer: AIOKafkaProducer, msg: ConsumerRecord, error: str):
#     dlq_topic = f"{msg.topic}.dlq"
#     payload = {
#         "original_topic": msg.topic,
#         "partition": msg.partition,
#         "offset": msg.offset,
#         "timestamp": msg.timestamp,
#         "key": msg.key.decode() if msg.key else None,
#         "payload": msg.value,
#         "error": str(error),
#     }

#     try:
#         await producer.send_and_wait(dlq_topic, payload)
#     except Exception as e:
#         logger.exception(
#             f"[{service_name}] failed to send message to DLQ {dlq_topic}: {e}"
#         )
#         raise


# async def handle_message(msg: ConsumerRecord, retry_count=3):

#     for attempt in range(retry_count):
#         try:
#             logger.info(
#                 f"[{service_name}] processing message from partition {msg.partition}: {msg.value} on topic: {msg.topic}"
#             )
#             handler = HANDLERS.get(msg.topic)
#             if handler:
#                 await handler(msg.value)
#             else:
#                 logger.warning(
#                     f"[{service_name}] no handler found for topic: {msg.topic}"
#                 )
#                 raise ValueError(f"No handler for topic {msg.topic}")
#             return

#         except ValueError:
#             raise

#         except Exception as e:
#             if attempt >= retry_count - 1:
#                 logger.error(
#                     f"[{service_name}] error processing {msg.topic} -> [DLQ]: {e}"
#                 )
#                 try:
#                     producer = get_producer()
#                     await send_to_dlq(producer, msg, e)
#                     return
#                 except Exception as dlq_error:
#                     logger.exception(
#                         f"[{service_name}] failed to send message to DLQ after retries: {dlq_error}"
#                     )
#                     raise

#             await asyncio.sleep(2**attempt)  # Exponential backoff


# async def partition_worker(
#     partition: TopicPartition, queue: asyncio.Queue[ConsumerRecord]
# ):
#     # topic_partition = TopicPartition(partition)

#     try:
#         while True:
#             msg = await queue.get()
#             # partition_offset = OffsetAndMetadata(msg.offset + 1, "")

#             try:
#                 await handle_message(msg)
#                 # await consumer.commit({topic_partition: partition_offset})

#             except Exception as e:
#                 logger.error(
#                     f"[{service_name}] error in partition worker for partition {partition}: {e}"
#                 )

#             finally:
#                 queue.task_done()
#                 handle_partition_backpressure(partition)

#     except asyncio.CancelledError:
#         logger.warning(f"[{service_name}] consumer partition {partition} cancelled")
#         pass

#     finally:
#         # draining the queue is not needed since messages will be re-processed after rebalance
#         # await drain_partition_queue(partition)

#         handle_partition_backpressure(partition)


# async def consume():
#     try:
#         async for msg in consumer:
#             topic_partition = TopicPartition(msg.topic, msg.partition)
#             queue = partition_queues[topic_partition]

#             await queue.put(msg)

#             # try:
#             #     queue.put_nowait(msg)
#             # except asyncio.QueueFull as e:
#             #     producer = get_producer()
#             #     await send_to_dlq(producer, msg, e)
#             handle_partition_backpressure(
#                 topic_partition
#             )  # more relevant for auto-commit false

#     except asyncio.CancelledError:
#         logger.warning(f"[{service_name}] consumer cancelled")
#         pass

#     except Exception as e:
#         logger.error(f"[{service_name}] handler error: {e}")

#     finally:
#         logger.info(f"[{service_name}] consumer stopping")


# async def start_consumer():
#     global consumer
#     if consumer is None:
#         consumer = get_consumer()

#     await consumer.start()
#     await consume()


# async def shutdown_consumer():
#     if not consumer:
#         return

#     # drain queues
#     for queue in partition_queues.values():
#         # await queue.join()
#         try:
#             await asyncio.wait_for(queue.join(), timeout=30)
#         except asyncio.TimeoutError:
#             logger.warning(f"[{service_name}] timeout while draining queues")

#     # cancel current tasks
#     for task in partition_tasks.values():
#         task.cancel()

#     await asyncio.gather(*partition_tasks.values(), return_exceptions=True)

#     await consumer.stop()

#     logger.info(f"[{service_name}] consumer shutdown complete")
