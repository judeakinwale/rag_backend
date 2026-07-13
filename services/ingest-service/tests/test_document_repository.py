from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from rag_packages.contracts.dto.document import CreateDocumentRequest, UpdateDocumentRequest
from app.repositories.document_repository import DocumentRepository


@pytest.mark.asyncio
async def test_get_all_delegates_to_get_model_page(monkeypatch):
    db = AsyncMock()
    repo = DocumentRepository(db)
    documents = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    get_model_page = AsyncMock(return_value=(documents, 2))
    monkeypatch.setattr("app.repositories.document_repository.get_model_page", get_model_page)

    result = await repo.get_all()

    assert result == (documents, 2)
    get_model_page.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_builds_document_and_adds_to_session():
    db = SimpleNamespace(add=Mock())
    repo = DocumentRepository(db)
    payload = CreateDocumentRequest(
        name="Test Document",
        file_url="https://contoso.example/docs/test.pdf",
        library_name="Shared Documents",
        library_id="library-1",
        site_url="https://contoso.sharepoint.com/sites/demo",
        parent_folder_path="/general",
        source="sharepoint",
        file_metadata={"etag": "etag-1"},
        last_modified="2024-01-01T00:00:00Z",
        file_type="pdf",
        file_size=100,
    )

    document = await repo.create(payload)

    assert document.name == payload.name
    assert document.file_url == payload.file_url
    assert document.source == payload.source
    db.add.assert_called_once_with(document)


@pytest.mark.asyncio
async def test_create_multiple_builds_documents_and_adds_all_to_session():
    db = SimpleNamespace(add_all=Mock())
    repo = DocumentRepository(db)
    payloads = [
        CreateDocumentRequest(
            name="Doc One",
            file_url="https://contoso.example/docs/1.pdf",
            library_name="Shared Documents",
            library_id="library-1",
            site_url="https://contoso.sharepoint.com/sites/demo",
            parent_folder_path="/general",
            source="sharepoint",
            file_metadata={"etag": "etag-1"},
            last_modified="2024-01-01T00:00:00Z",
            file_type="pdf",
            file_size=100,
        ),
        CreateDocumentRequest(
            name="Doc Two",
            file_url="https://contoso.example/docs/2.pdf",
            library_name="Shared Documents",
            library_id="library-1",
            site_url="https://contoso.sharepoint.com/sites/demo",
            parent_folder_path="/general",
            source="sharepoint",
            file_metadata={"etag": "etag-2"},
            last_modified="2024-01-02T00:00:00Z",
            file_type="pdf",
            file_size=200,
        ),
    ]

    documents = await repo.create_multiple(payloads)

    assert len(documents) == 2
    assert [document.name for document in documents] == ["Doc One", "Doc Two"]
    db.add_all.assert_called_once_with(documents)


@pytest.mark.asyncio
async def test_get_by_id_uses_session_get():
    document = SimpleNamespace(id=10)
    db = AsyncMock()
    db.get.return_value = document
    repo = DocumentRepository(db)

    result = await repo.get_by_id(10)

    assert result is document
    db.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_last_batch_document_returns_single_document():
    document = SimpleNamespace(id=7)
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalar_one_or_none=Mock(return_value=document)
    )
    repo = DocumentRepository(db)

    result = await repo.get_last_batch_document("sharepoint")

    assert result is document
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_applies_fields_to_existing_document():
    timestamp = datetime(2024, 2, 1, tzinfo=UTC)
    document = SimpleNamespace(
        id=3,
        name="Old Name",
        file_size=10,
        ingest_status="started",
        last_modified=datetime(2024, 1, 1, tzinfo=UTC),
    )
    db = AsyncMock()
    repo = DocumentRepository(db)
    payload = UpdateDocumentRequest(
        name="New Name",
        file_size=25,
        ingest_status="completed",
        last_modified="2024-02-01T00:00:00Z",
    )
    repo.get_by_id = AsyncMock(return_value=document)

    result = await repo.update(3, payload)

    assert result is document
    assert document.name == "New Name"
    assert document.file_size == 25
    assert document.ingest_status == "completed"
    assert document.last_modified == timestamp


@pytest.mark.asyncio
async def test_update_returns_none_when_document_missing():
    db = AsyncMock()
    repo = DocumentRepository(db)
    repo.get_by_id = AsyncMock(return_value=None)

    result = await repo.update(999, UpdateDocumentRequest(name="Missing"))

    assert result is None


@pytest.mark.asyncio
async def test_delete_removes_existing_document():
    document = SimpleNamespace(id=5)
    db = AsyncMock()
    repo = DocumentRepository(db)
    repo.get_by_id = AsyncMock(return_value=document)

    result = await repo.delete(5)

    assert result is document
    db.delete.assert_awaited_once_with(document)


@pytest.mark.asyncio
async def test_delete_returns_none_when_document_missing():
    db = AsyncMock()
    repo = DocumentRepository(db)
    repo.get_by_id = AsyncMock(return_value=None)

    result = await repo.delete(123)

    assert result is None
    db.delete.assert_not_called()
