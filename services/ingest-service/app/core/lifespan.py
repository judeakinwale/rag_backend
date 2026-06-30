from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.db import engine
from app.core.redis import r
from app.events.events import EVENTS
from app.kafka_consumer import TOPICS, HANDLERS
from app.scheduler.polling import SharePointIngestPoller

# this would be moved to the shared packages later
from app.services.sharepoint_service import SharepointService, SharepointConfig
from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.shared.kafka.consumer import KafkaConsumer


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
        config = SharepointConfig(
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET,
            tenant_id=settings.AZURE_TENANT_ID,
            site_url=settings.SHAREPOINT_SITE_URL,
        )
        app.state.sharepoint_service = SharepointService(config=config)

    except Exception as e:
        print(f"Error initializing SharepointService: {e}")
        app.state.sharepoint_service = None

    kafka_producer = app.state.kafka_producer
    sharepoint_service = app.state.sharepoint_service
    if kafka_producer and sharepoint_service:
        poller = SharePointIngestPoller(
            kafka_producer=kafka_producer,
            sharepoint_service=sharepoint_service,
        )
        await poller.start()
        app.state.sharepoint_ingest_poller = poller

    yield

    poller = app.state.sharepoint_ingest_poller
    if poller:
        await poller.stop()
        app.state.sharepoint_ingest_poller = None

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
