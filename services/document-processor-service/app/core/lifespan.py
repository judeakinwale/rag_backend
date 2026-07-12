from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.db import engine
from app.core.redis import r
from app.events.events import EVENTS
from app.kafka_consumer import TOPICS, HANDLERS

from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.shared.kafka.consumer import KafkaConsumer
from rag_packages.shared.processing.document_processor import DocumentProcessor
from rag_packages.shared.processing.qdrant import QdrantService, QdrantServiceConfig


@asynccontextmanager
async def lifespan(app: FastAPI):

    # ? duplicate initialization in container.py, for event handling
    # ! this is still important
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
        qdrant_service_config = QdrantServiceConfig(
            collection_name="documents",
            host=settings.QDRANT_HOSTNAME,
            port=settings.QDRANT_PORT,
            grpc_port=settings.QDRANT_GRPC_PORT,
        )
        app.state.qdrant_service = QdrantService(config=qdrant_service_config)
        app.state.document_processor_service = DocumentProcessor(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
    except Exception as e:
        print(f"Error initializing QdrantService or DocumentProcessor service: {e}")
        app.state.qdrant_service = None
        app.state.document_processor_service = None

    yield

    kafka_producer = app.state.kafka_producer
    if kafka_producer:
        await kafka_producer.stop()
        app.state.kafka_producer = None

    kafka_consumer = app.state.kafka_consumer
    if kafka_consumer:
        await kafka_consumer.stop()
        app.state.kafka_consumer = None

    qdrant_service = app.state.qdrant_service
    if qdrant_service:
        await qdrant_service.close()
        app.state.qdrant_service = None

    app.state.document_processor_service = None

    await engine.dispose()
    await r.close()
