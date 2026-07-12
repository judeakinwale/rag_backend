import asyncio
from typing import Any
from app.core.config import settings
from app.core.redis import r
from rag_packages.shared.kafka.producers.ingest import IngestProducer
from app.producers.vector_document_producer import VectorDocumentProducer
from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.shared.kafka.consumer import KafkaConsumer
from rag_packages.shared.processing.document_processor import DocumentProcessor
from rag_packages.shared.processing.qdrant import QdrantService, QdrantServiceConfig


# ? this is modified to handle a second instance of the producer,
# ? qdrant and document processor from the lifespan.py instead
class Container:
    def __init__(self):
        self._producer_lock = asyncio.Lock()
        self._consumer_lock = asyncio.Lock()
        self._producer: KafkaProducer | None = None
        self._consumer: KafkaConsumer | None = None

        self.qdrant_config = QdrantServiceConfig(
            collection_name="documents",
            host=settings.QDRANT_HOSTNAME,
            port=settings.QDRANT_PORT,
            grpc_port=settings.QDRANT_GRPC_PORT,
        )
        self.qdrant_service = QdrantService(config=self.qdrant_config)
        self.document_processor_service = DocumentProcessor(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

    async def producer(self) -> KafkaProducer:
        if self._producer is not None:
            return self._producer

        async with self._producer_lock:
            if self._producer is not None:
                return self._producer

            if self._producer is None:
                self._producer = KafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    service_name=settings.APP_NAME,
                )
                await self._producer.start()

            return self._producer

    async def consumer(
        self, topics: list[str], handlers: dict[str, Any], events: dict[str, Any]
    ) -> KafkaConsumer:
        if self._consumer is not None:
            return self._consumer

        async with self._consumer_lock:
            if self._consumer is not None:
                return self._consumer

            if self._consumer is None:
                producer = await self.producer()

                self._consumer = KafkaConsumer(
                    topics=topics,
                    handlers=handlers,
                    event_models=events,
                    dlq_producer=producer,
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    service_name=settings.APP_NAME,
                )

                await self._consumer.start()

            return self._consumer

    async def ingest_producer(
        self, producer: KafkaProducer | None = None
    ) -> IngestProducer:
        producer = producer or await self.producer()
        return IngestProducer(producer)

    async def vector_document_producer(
        self, producer: KafkaProducer | None = None
    ) -> VectorDocumentProducer:
        producer = producer or await self.producer()
        return VectorDocumentProducer(producer)

    # _____________________________________________________________________________

    async def close(self):
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

        await self.qdrant_service.close()
        self.qdrant_service = None

        # await engine.dispose()
        await r.close()


container = Container()
