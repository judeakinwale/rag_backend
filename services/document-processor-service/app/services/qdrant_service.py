import asyncio

# import numpy as np
import uuid
from datetime import datetime
from typing import Any

from fastembed import TextEmbedding
from qdrant_client import AsyncQdrantClient, models
from rag_packages.contracts.dto.shared_dto import BaseDTO
from app.core.config import settings
from app.dto.vector_document_dto import CreateVectorDocumentRequest


class CollectionPayload(BaseDTO):
    payload: CreateVectorDocumentRequest | None = None
    vector: list[float] | list[list[float]] | None = None


class QdrantService:
    def __init__(self, collection_name: str = "documents"):
        self.client: AsyncQdrantClient | None = None
        self.collection_name = collection_name
        self.model_name = "BAAI/bge-base-en"
        self.embedding_model = TextEmbedding(
            model_name=self.model_name,
            lazy_load=True,
        )
        self.vector_params: models.VectorParams | None = None

    async def get_client(self) -> AsyncQdrantClient:
        if self.client is not None:
            return self.client

        if settings.QDRANT_GRPC_PORT:
            self.client = AsyncQdrantClient(
                host=settings.QDRANT_HOSTNAME,
                grpc_port=settings.QDRANT_GRPC_PORT,
                prefer_grpc=True,
            )
            return self.client

        self.client = AsyncQdrantClient(
            host=settings.QDRANT_HOSTNAME, port=settings.QDRANT_PORT
        )
        return self.client

    async def get_vector_params(
        self, client: AsyncQdrantClient | None = None
    ) -> models.VectorParams:
        if self.vector_params is not None:
            return self.vector_params

        client = client or await self.get_client()
        size = client.get_embedding_size(self.model_name)
        self.vector_params = models.VectorParams(
            size=size, distance=models.Distance.COSINE
        )
        return self.vector_params

    async def create_collection(self, recreate: bool = False) -> bool:
        client = await self.get_client()
        vector_params = await self.get_vector_params(client)

        if recreate:
            return await client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=vector_params,
            )

        return await client.create_collection(
            collection_name=self.collection_name,
            vectors_config=vector_params,
        )

    async def generate_vector_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise ValueError("texts are required to generate embeddings.")

        # NOTE: if unstable under heavy concurrency, protect embedding calls with an asyncio.Lock or use a small worker pool.
        embeddings = await asyncio.to_thread(
            lambda: [
                embedding.toList() for embedding in self.embedding_model.embed(texts)
            ]
        )
        if not embeddings:
            raise ValueError("Failed to generate embeddings for the supplied texts.")

        return [embedding.tolist() for embedding in embeddings]

    def get_point(self, item: CollectionPayload, index: int) -> models.PointStruct:
        if item.payload is None:
            raise ValueError("Collection payload is required.")

        if item.vector is None:
            raise ValueError("Vector embedding is required.")

        vector = item.vector

        item.payload.chunk_id = item.payload.chunk_id or index
        payload = item.payload.model_dump()

        point = models.PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=payload,
        )
        return point

    def get_points(self, items: list[CollectionPayload]) -> list[models.PointStruct]:
        points = [self.get_point(item, idx) for idx, item in enumerate(items)]
        return points

    async def upsert_points(
        self, points: list[models.PointStruct]
    ) -> models.UpdateResult:
        client = await self.get_client()

        # NOTE: consider splitting the data into chunks to avoid hitting the server's payload size limit
        # or use `upload_collection` or `upload_points` methods which handle this for you
        # WARNING: uploading points one-by-one is not recommended due to requests overhead
        result = await client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        return result

    async def upload_points(
        self, points: list[models.PointStruct]
    ) -> models.UpdateResult:
        client = await self.get_client()

        result = await client.upload_collection(
            collection_name=self.collection_name,
            points=points,
        )
        return result

    async def add_chunks_to_collection(
        self, chunks: list[CreateVectorDocumentRequest]
    ) -> list[models.UpdateResult]:
        initiated_at = datetime.now()

        valid_chunks: list[CreateVectorDocumentRequest] = []
        for chunk in chunks:
            if not chunk.text.strip():
                continue

            chunk.text = chunk.text.strip()
            chunk.initiated_at = chunk.initiated_at or initiated_at
            valid_chunks.append(chunk)

        if not valid_chunks:
            raise ValueError("No valid chunks to add to the collection.")

        vectors = await self.generate_vector_embeddings(
            [chunk.text for chunk in valid_chunks]
        )

        if len(vectors) != len(valid_chunks):
            raise RuntimeError(
                f"Embedding count does not match the number of valid chunks: {len(vectors)} != {len(valid_chunks)}."
            )

        payload_list = [
            CollectionPayload(payload=chunk, vector=vector)
            for chunk, vector in zip(valid_chunks, vectors)
        ]
        points = self.get_points(payload_list)
        batched_points = [points[i : i + 100] for i in range(0, len(points), 100)]

        results = [await self.upsert_points(batch) for batch in batched_points]
        # results = await asyncio.gather(
        #     *[self.upsert_points(batch) for batch in batched_points]
        # )

        return results

    async def get_matching_vectors(
        self,
        query_vector: list[float] | None = None,
        limit: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> models.QueryResponse:
        client = await self.get_client()

        if query_vector is None:
            raise ValueError("query_vector is required for vector search.")

        filter = filter or {}

        # # ? example
        # condition = models.FieldCondition(
        #     # Condition based on values of `rand_number` field.
        #     key="rand_number",
        #     # Select only those results where `rand_number` >= 3
        #     range=models.Range(gte=3),
        #     # match=models.MatchValue(value=3),
        # )
        # query_filter = (
        #     # These conditions are required for search results
        #     models.Filter(must=[condition]),
        # )

        conditions = [
            models.FieldCondition(key=key, match=models.MatchValue(value=value))
            for key, value in filter.items()
        ]
        query_filter = models.Filter(must=conditions) if conditions else None

        hits = await client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,  # Return [limit] closest points
        )
        return hits

    async def delete_collection(self) -> bool:
        client = await self.get_client()
        result = await client.delete_collection(
            collection_name=self.collection_name,
        )
        return result

    async def close(self):
        if self.client is None:
            return

        await self.client.close()
