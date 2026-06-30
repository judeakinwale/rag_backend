from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.dto.document_dto import CreateDocumentRequest, UpdateDocumentRequest
from app.events.document_events import DocumentStartedEvent, DocumentDeletedEvent, DocumentUpdatedEvent
from app.models.document import RoleOption
from app.services.document_service import DocumentService


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


def make_document(document_id=1, email="document@example.com", name="Document", roles=None):
    return SimpleNamespace(
        id=document_id,
        email=email,
        name=name,
        password="hashed-password",
        roles=roles or [RoleOption.DOCUMENT],
    )


@pytest.mark.asyncio
async def test_get_documents_maps_entities_to_responses():
    repo = SimpleNamespace(get_all=AsyncMock(return_value=[make_document(), make_document(2)]))
    producer = SimpleNamespace()
    service = DocumentService(FakeUnitOfWork(), repo, producer)

    result = await service.get_untracked_documents()

    assert [document.id for document in result] == [1, 2]
    assert all(document.email.endswith("@example.com") for document in result)


@pytest.mark.asyncio
async def test_create_document_flushes_and_publishes_created_event():
    document = make_document()
    uow = FakeUnitOfWork()
    repo = SimpleNamespace(create=AsyncMock(return_value=document))
    producer = SimpleNamespace(document_created=AsyncMock())
    service = DocumentService(uow, repo, producer)
    payload = CreateDocumentRequest(
        email="document@example.com",
        name="Document",
        password="secret",
        roles=[RoleOption.DOCUMENT],
    )

    result = await service.create_document(payload)

    repo.create.assert_awaited_once_with(payload)
    uow.session.flush.assert_awaited_once()
    producer.document_created.assert_awaited_once()
    event = producer.document_created.await_args.args[0]
    assert isinstance(event, DocumentStartedEvent)
    assert event.id == document.id
    assert result.id == document.id


@pytest.mark.asyncio
async def test_get_document_by_id_returns_none_when_missing():
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    service = DocumentService(FakeUnitOfWork(), repo, SimpleNamespace())

    result = await service.get_document_by_id(404)

    assert result is None


@pytest.mark.asyncio
async def test_get_document_by_id_maps_model_to_response():
    document = make_document(8)
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=document))
    service = DocumentService(FakeUnitOfWork(), repo, SimpleNamespace())

    result = await service.get_document_by_id(8)

    assert result is not None
    assert result.id == 8
    assert result.email == document.email


@pytest.mark.asyncio
async def test_update_document_publishes_updated_fields():
    document = make_document(9, name="Updated Document")
    uow = FakeUnitOfWork()
    repo = SimpleNamespace(update=AsyncMock(return_value=document))
    producer = SimpleNamespace(document_updated=AsyncMock())
    service = DocumentService(uow, repo, producer)
    payload = UpdateDocumentRequest(name="Updated Document", password="new-secret")

    result = await service.update_document(9, payload)

    repo.update.assert_awaited_once_with(9, payload)
    producer.document_updated.assert_awaited_once()
    event = producer.document_updated.await_args.args[0]
    assert isinstance(event, DocumentUpdatedEvent)
    assert event.updated == ["name", "password"]
    assert result is not None
    assert result.id == 9


@pytest.mark.asyncio
async def test_update_document_returns_none_without_event_when_missing():
    repo = SimpleNamespace(update=AsyncMock(return_value=None))
    producer = SimpleNamespace(document_updated=AsyncMock())
    service = DocumentService(FakeUnitOfWork(), repo, producer)

    result = await service.update_document(404, UpdateDocumentRequest(name="Missing"))

    assert result is None
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
    assert result is not None
    assert result.id == 12


@pytest.mark.asyncio
async def test_delete_document_returns_none_without_event_when_missing():
    repo = SimpleNamespace(delete=AsyncMock(return_value=None))
    producer = SimpleNamespace(document_deleted=AsyncMock())
    service = DocumentService(FakeUnitOfWork(), repo, producer)

    result = await service.delete_document(77)

    assert result is None
    producer.document_deleted.assert_not_awaited()