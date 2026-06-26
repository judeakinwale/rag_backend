from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.dto.ingest_dto import CreateIngestRequest, UpdateIngestRequest
from app.events.ingest_events import IngestCreatedEvent, IngestDeletedEvent, IngestUpdatedEvent
from app.models.ingest import RoleOption
from app.services.ingest_service import IngestService


class FakeUnitOfWork:
    def __init__(self):
        self.session = SimpleNamespace(flush=AsyncMock())
        self.entered = 0
        self.exited = 0

    async def __aenter__(self):
        self.entered += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited += 1


def make_ingest(ingest_id=1, email="ingest@example.com", name="Ingest", roles=None):
    return SimpleNamespace(
        id=ingest_id,
        email=email,
        name=name,
        password="hashed-password",
        roles=roles or [RoleOption.INGEST],
    )


@pytest.mark.asyncio
async def test_get_ingests_maps_entities_to_responses():
    repo = SimpleNamespace(get_all=AsyncMock(return_value=[make_ingest(), make_ingest(2)]))
    producer = SimpleNamespace()
    service = IngestService(FakeUnitOfWork(), repo, producer)

    result = await service.get_ingests()

    assert [ingest.id for ingest in result] == [1, 2]
    assert all(ingest.email.endswith("@example.com") for ingest in result)


@pytest.mark.asyncio
async def test_create_ingest_flushes_and_publishes_created_event():
    ingest = make_ingest()
    uow = FakeUnitOfWork()
    repo = SimpleNamespace(create=AsyncMock(return_value=ingest))
    producer = SimpleNamespace(ingest_created=AsyncMock())
    service = IngestService(uow, repo, producer)
    payload = CreateIngestRequest(
        email="ingest@example.com",
        name="Ingest",
        password="secret",
        roles=[RoleOption.INGEST],
    )

    result = await service.create_ingest(payload)

    repo.create.assert_awaited_once_with(payload)
    uow.session.flush.assert_awaited_once()
    producer.ingest_created.assert_awaited_once()
    event = producer.ingest_created.await_args.args[0]
    assert isinstance(event, IngestCreatedEvent)
    assert event.id == ingest.id
    assert result.id == ingest.id


@pytest.mark.asyncio
async def test_get_ingest_by_id_returns_none_when_missing():
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    service = IngestService(FakeUnitOfWork(), repo, SimpleNamespace())

    result = await service.get_ingest_by_id(404)

    assert result is None


@pytest.mark.asyncio
async def test_get_ingest_by_id_maps_model_to_response():
    ingest = make_ingest(8)
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=ingest))
    service = IngestService(FakeUnitOfWork(), repo, SimpleNamespace())

    result = await service.get_ingest_by_id(8)

    assert result is not None
    assert result.id == 8
    assert result.email == ingest.email


@pytest.mark.asyncio
async def test_update_ingest_publishes_updated_fields():
    ingest = make_ingest(9, name="Updated Ingest")
    uow = FakeUnitOfWork()
    repo = SimpleNamespace(update=AsyncMock(return_value=ingest))
    producer = SimpleNamespace(ingest_updated=AsyncMock())
    service = IngestService(uow, repo, producer)
    payload = UpdateIngestRequest(name="Updated Ingest", password="new-secret")

    result = await service.update_ingest(9, payload)

    repo.update.assert_awaited_once_with(9, payload)
    producer.ingest_updated.assert_awaited_once()
    event = producer.ingest_updated.await_args.args[0]
    assert isinstance(event, IngestUpdatedEvent)
    assert event.updated == ["name", "password"]
    assert result is not None
    assert result.id == 9


@pytest.mark.asyncio
async def test_update_ingest_returns_none_without_event_when_missing():
    repo = SimpleNamespace(update=AsyncMock(return_value=None))
    producer = SimpleNamespace(ingest_updated=AsyncMock())
    service = IngestService(FakeUnitOfWork(), repo, producer)

    result = await service.update_ingest(404, UpdateIngestRequest(name="Missing"))

    assert result is None
    producer.ingest_updated.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_ingest_publishes_deleted_event():
    ingest = make_ingest(12)
    repo = SimpleNamespace(delete=AsyncMock(return_value=ingest))
    producer = SimpleNamespace(ingest_deleted=AsyncMock())
    service = IngestService(FakeUnitOfWork(), repo, producer)

    result = await service.delete_ingest(12)

    producer.ingest_deleted.assert_awaited_once()
    event = producer.ingest_deleted.await_args.args[0]
    assert isinstance(event, IngestDeletedEvent)
    assert event.id == 12
    assert result is not None
    assert result.id == 12


@pytest.mark.asyncio
async def test_delete_ingest_returns_none_without_event_when_missing():
    repo = SimpleNamespace(delete=AsyncMock(return_value=None))
    producer = SimpleNamespace(ingest_deleted=AsyncMock())
    service = IngestService(FakeUnitOfWork(), repo, producer)

    result = await service.delete_ingest(77)

    assert result is None
    producer.ingest_deleted.assert_not_awaited()