from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.db import engine
from app.core.redis import r
from app.events.events import EVENTS
from app.kafka_consumer import TOPICS, HANDLERS
from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.shared.kafka.consumer import KafkaConsumer
from rag_packages.shared.ai.openai import OpenAIService


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.sharepoint_ingest_poller = None

    try:
        app.state.kafka_producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            service_name=settings.APP_NAME,
        )
        await app.state.kafka_producer.start()

        app.state.kafka_consumer = KafkaConsumer(
            topics=TOPICS,
            handlers=HANDLERS,
            event_models=EVENTS,
            dlq_producer=app.state.kafka_producer,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            service_name=settings.APP_NAME,
        )
        await app.state.kafka_consumer.start()

    except Exception as e:
        print(f"Error initializing Kafka producer and consumer: {e}")
        app.state.kafka_producer = None
        app.state.kafka_consumer = None

    try:
        app.state.openai_service = OpenAIService(
            api_key=settings.OPENAI_API_KEY,
            webhook_secret=settings.OPENAI_WEBHOOK_SECRET,
        )
    except Exception as e:
        print(f"Error initializing OpenAIService: {e}")
        app.state.openai_service = None
        raise e

    yield

    kafka_producer = app.state.kafka_producer
    if kafka_producer:
        await kafka_producer.stop()
        app.state.kafka_producer = None

    kafka_consumer = app.state.kafka_consumer
    if kafka_consumer:
        await kafka_consumer.stop()
        app.state.kafka_consumer = None

    openai_service = app.state.openai_service
    if openai_service:
        app.state.openai_service = None

    await engine.dispose()
    await r.close()
