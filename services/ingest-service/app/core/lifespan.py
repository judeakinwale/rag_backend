from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.db import engine
from app.core.redis import r
from app.events.events import EVENTS
from app.kafka_consumer import TOPICS, HANDLERS

# this would be moved to the shared packages later
from app.services.sharepoint_service import SharepointService, SharepointConfig
from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.shared.kafka.consumer import KafkaConsumer


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        config = SharepointConfig(
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET,
            tenant_id=settings.AZURE_TENANT_ID,
        )
        app.state.sharepoint_service = SharepointService(config=config)

    except Exception as e:
        print(f"Error initializing SharepointService: {e}")
        print(
            {
                "client_id": settings.AZURE_CLIENT_ID,
                "client_secret": settings.AZURE_CLIENT_SECRET,
                "tenant_id": settings.AZURE_TENANT_ID,
            }
        )
        app.state.sharepoint_service = None

    yield

    kafka_producer = app.state.kafka_producer
    if kafka_producer:
        await kafka_producer.stop()
        app.state.kafka_producer = None

    kafka_consumer = app.state.kafka_consumer
    if kafka_consumer:
        await kafka_consumer.stop()
        app.state.kafka_consumer = None

    await engine.dispose()
    await r.close()
