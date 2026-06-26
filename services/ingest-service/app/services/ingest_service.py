import orjson
from app.repositories.ingest_repository import IngestRepository
from app.producers.ingest_producer import IngestProducer
from app.events.ingest_events import IngestCreatedEvent, IngestUpdatedEvent, IngestDeletedEvent
from app.models.ingest import Ingest
from app.core.redis import generate_cache_key, r
from app.dto.ingest_dto import CreateIngestRequest, UpdateIngestRequest, IngestResponse
from rag_packages.shared.database.uow import UnitOfWork


class IngestService:
    def __init__(
        self,
        uow: UnitOfWork,
        repo: IngestRepository,
        producer: IngestProducer,
        # outbox_repo: None = None,
    ):
        self.uow = uow
        self.repo = repo
        self.producer = producer

    async def get_ingests(self) -> list[IngestResponse]:
        cache_key = generate_cache_key(str("all"))
        cached = await r.get(cache_key)

        if cached is not None:
            try:
                ingest_arr = orjson.loads(cached)  # Ensure the cached data is valid JSON
                return [IngestResponse.model_validate_json(ingest) for ingest in ingest_arr]

            except orjson.JSONDecodeError:
                print(
                    f"[ingest-service] Failed to decode cached data for key {cache_key}. Invalidating cache."
                )
                await r.delete(cache_key)  # invalidate corrupted cache

        ingests = await self.repo.get_all()
        valid_ingests = [IngestResponse.model_validate(ingest) for ingest in ingests]

        await r.set(cache_key, orjson.dumps(valid_ingests))
        return valid_ingests

    # TODO: confirm this works as expected
    async def create_ingest(self, payload: CreateIngestRequest) -> IngestResponse:
        async with self.uow:
            ingest: Ingest = await self.repo.create(payload)

            # ensure the ingest is persisted and
            await self.uow.session.flush()
            # access the persisted ingest's id before committing and sending the event
            ingest_id = ingest.id
            print(f"Created ingest with ID: {ingest_id}")
            print(f"Ingest details: {ingest}")

            # outbox_repo.add(
            #     event_type="ingest_created",
            #     payload={...}
            # )

        event = IngestCreatedEvent.model_validate(ingest)
        await self.producer.ingest_created(event)

        return IngestResponse.model_validate(ingest)

    async def get_ingest_by_id(self, ingest_id: int) -> IngestResponse | None:
        cache_key = generate_cache_key(str(ingest_id))
        cached = await r.get(cache_key)

        if cached is not None:
            return IngestResponse.model_validate_json(cached)

        ingest = await self.repo.get_by_id(ingest_id)
        if ingest is None:
            return None

        valid_ingest = IngestResponse.model_validate(ingest)

        await r.set(cache_key, valid_ingest.model_dump_json())
        return valid_ingest

    async def update_ingest(
        self, ingest_id: int, payload: UpdateIngestRequest
    ) -> IngestResponse | None:
        async with self.uow:
            ingest: Ingest | None = await self.repo.update(ingest_id, payload)
            if ingest is None:
                return None

        event = IngestUpdatedEvent.model_validate(ingest)
        event.updated = list(payload.model_dump(exclude_unset=True).keys())
        await self.producer.ingest_updated(event)

        return IngestResponse.model_validate(ingest)

    async def delete_ingest(self, ingest_id: int) -> IngestResponse | None:
        async with self.uow:
            ingest: Ingest | None = await self.repo.delete(ingest_id)
            if ingest is None:
                return None

        event = IngestDeletedEvent.model_validate(ingest)
        await self.producer.ingest_deleted(event)

        return IngestResponse.model_validate(ingest)
