from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import orjson
import pytest

from app.dto.document_dto import CreateDocumentRequest, UpdateDocumentRequest
from app.events.document_events import DocumentCreatedEvent, DocumentDeletedEvent, DocumentUpdatedEvent
from app.services import document_service as document_service_module
from app.services.document_service import DocumentService
from rag_packages.shared.database.query import QueryParams
from rag_packages.shared.exception.exception import NotFoundException


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


class FakeRedis:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.get = AsyncMock(side_effect=self.values.get)
        self.set = AsyncMock(side_effect=self._set)
        self.delete = AsyncMock(side_effect=self._delete)

    async def _set(self, key, value):
        self.values[key] = value

    async def _delete(self, key):
        self.values.pop(key, None)


def make_document(document_id=1, ingest_status="started"):
    timestamp = datetime(2024, 1, 1, tzinfo=UTC)
    return SimpleNamespace(
        id=document_id,
        name=f"Document {document_id}",
        file_url=f"https://contoso.example/docs/{document_id}.pdf",
        library_name="Shared Documents",
        library_id="library-1",
        site_url="https://contoso.sharepoint.com/sites/demo",
        parent_folder_path="/general",
        source="sharepoint",
        file_metadata={"etag": f"etag-{document_id}"},
        last_modified=timestamp,
        file_type="pdf",
        file_size=1024,
        ingest_initiated_at=timestamp,
        ingest_status=ingest_status,
        prev_batch_ingest_init=None,
        created_at=timestamp,
        created_by_id=None,
        updated_at=timestamp,
        updated_by_id=None,
        is_active=True,
        is_deleted=False,
    )


def make_create_payload():
    return CreateDocumentRequest(
        name="Quarterly Report",
        file_url="https://contoso.example/docs/report.pdf",
        library_name="Shared Documents",
        library_id="library-1",
        site_url="https://contoso.sharepoint.com/sites/demo",
        parent_folder_path="/reports",
        source="sharepoint",
        file_metadata={"etag": "abc"},
        last_modified=datetime(2024, 1, 1, tzinfo=UTC),
        file_type="pdf",
        file_size=2048,
    )


@pytest.mark.asyncio
async def test_get_documents_maps_entities_to_responses_and_count(monkeypatch):
    redis_client = FakeRedis()
    monkeypatch.setattr(document_service_module, "r", redis_client)

    repo = SimpleNamespace(
        get_all=AsyncMock(return_value=([make_document(), make_document(2)], 2))
    )
    service = DocumentService(FakeUnitOfWork(), repo, SimpleNamespace())

    documents, count = await service.get_documents(QueryParams(page=1, size=10))

    assert count == 2
    assert [document.id for document in documents] == [1, 2]
    repo.get_all.assert_awaited_once()
    redis_client.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_documents_uses_cached_payload(monkeypatch):
    cached_documents = [
        {
            "id": 1,
            "name": "Cached Document",
            "file_url": "https://contoso.example/docs/1.pdf",
            "site_url": "https://contoso.sharepoint.com/sites/demo",
            "source": "sharepoint",
            "file_metadata": {"etag": "cached"},
            "last_modified": "2024-01-01T00:00:00Z",
            "file_type": "pdf",
            "file_size": 1024,
            "ingest_initiated_at": "2024-01-01T00:00:00Z",
            "ingest_status": "started",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "is_active": True,
            "is_deleted": False,
        }
    ]
    redis_client = FakeRedis({"document_service:all": orjson.dumps((cached_documents, 1))})
    monkeypatch.setattr(document_service_module, "r", redis_client)
    monkeypatch.setattr(document_service_module, "generate_cache_key", lambda suffix: f"document_service:{suffix}")

    repo = SimpleNamespace(get_all=AsyncMock())
    service = DocumentService(FakeUnitOfWork(), repo, SimpleNamespace())

    documents, count = await service.get_documents()

    assert count == 1
    assert documents[0].id == 1
    repo.get_all.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_document_flushes_and_publishes_created_event(monkeypatch):
    redis_client = FakeRedis()
    monkeypatch.setattr(document_service_module, "r", redis_client)

    document = make_document()
    uow = FakeUnitOfWork()
    repo = SimpleNamespace(create=AsyncMock(return_value=document))
    producer = SimpleNamespace(document_created=AsyncMock())
    service = DocumentService(uow, repo, producer)
    payload = make_create_payload()

    result = await service.create_document(payload)

    repo.create.assert_awaited_once_with(payload)
    uow.session.flush.assert_awaited_once()
    producer.document_created.assert_awaited_once()
    event = producer.document_created.await_args.args[0]
    assert isinstance(event, DocumentCreatedEvent)
    assert event.id == document.id
    assert result.id == document.id


@pytest.mark.asyncio
async def test_get_document_by_id_raises_when_missing(monkeypatch):
    redis_client = FakeRedis()
    monkeypatch.setattr(document_service_module, "r", redis_client)

    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    service = DocumentService(FakeUnitOfWork(), repo, SimpleNamespace())

    with pytest.raises(NotFoundException):
        await service.get_document_by_id(404)


@pytest.mark.asyncio
async def test_get_document_by_id_maps_model_to_response(monkeypatch):
    redis_client = FakeRedis()
    monkeypatch.setattr(document_service_module, "r", redis_client)

    document = make_document(8)
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=document))
    service = DocumentService(FakeUnitOfWork(), repo, SimpleNamespace())

    result = await service.get_document_by_id(8)

    assert result.id == 8
    assert result.file_url == document.file_url
    redis_client.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_document_publishes_updated_fields():
    document = make_document(9)
    uow = FakeUnitOfWork()
    repo = SimpleNamespace(update=AsyncMock(return_value=document))
    producer = SimpleNamespace(document_updated=AsyncMock())
    service = DocumentService(uow, repo, producer)
    payload = UpdateDocumentRequest(name="Updated Document", ingest_status="processing")

    result = await service.update_document(9, payload)

    repo.update.assert_awaited_once_with(9, payload)
    producer.document_updated.assert_awaited_once()
    event = producer.document_updated.await_args.args[0]
    assert isinstance(event, DocumentUpdatedEvent)
    assert event.updated == ["name", "ingest_status"]
    assert result.id == 9


@pytest.mark.asyncio
async def test_update_document_raises_without_event_when_missing():
    repo = SimpleNamespace(update=AsyncMock(return_value=None))
    producer = SimpleNamespace(document_updated=AsyncMock())
    service = DocumentService(FakeUnitOfWork(), repo, producer)

    with pytest.raises(NotFoundException):
        await service.update_document(404, UpdateDocumentRequest(name="Missing"))

    producer.document_updated.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_document_publishes_deleted_event():
    document = make_document(12)
    repo = SimpleNamespace(delete=AsyncMock(return_value=document))
    producer = SimpleNamespace(document_deleted=AsyncMock())
    service = DocumentService(FakeUnitOfWork(), repo, producer)

    result = await service.delete_document(12)

    producer.document_deleted.assert_awaited_once()
    event = producer.document_deleted.await_args.args[0]
    assert isinstance(event, DocumentDeletedEvent)
    assert event.id == 12
    assert result.id == 12


@pytest.mark.asyncio
async def test_delete_document_raises_without_event_when_missing():
    repo = SimpleNamespace(delete=AsyncMock(return_value=None))
    producer = SimpleNamespace(document_deleted=AsyncMock())
    service = DocumentService(FakeUnitOfWork(), repo, producer)

    with pytest.raises(NotFoundException):
        await service.delete_document(77)

    producer.document_deleted.assert_not_awaited()
