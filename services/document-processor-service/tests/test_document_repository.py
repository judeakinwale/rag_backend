from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.dto.document_dto import CreateDocumentRequest, UpdateDocumentRequest
from app.repositories.document_repository import DocumentRepository


class FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class FakeExecuteResult:
    def __init__(self, values=None, value=None):
        self._values = values or []
        self._value = value

    def scalars(self):
        return FakeScalarResult(self._values)

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_get_all_returns_scalar_results():
    documents = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    db = AsyncMock()
    db.execute.return_value = FakeExecuteResult(values=documents)
    repo = DocumentRepository(db)

    result = await repo.get_all()

    assert result == documents
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_hashes_password(monkeypatch):
    db = SimpleNamespace(add=Mock())
    repo = DocumentRepository(db)
    payload = CreateDocumentRequest(
        email="document@example.com",
        name="Test Document",
        password="plain-text",
        roles=[RoleOption.ADMIN],
    )

    monkeypatch.setattr(
        "app.repositories.document_repository.hash_password",
        lambda password: f"hashed::{password}",
    )

    document = await repo.create(payload)

    assert document.email == payload.email
    assert document.name == payload.name
    assert document.password == "hashed::plain-text"
    assert document.roles == [RoleOption.ADMIN]
    db.add.assert_called_once_with(document)


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
async def test_get_by_email_returns_single_document():
    document = SimpleNamespace(id=7, email="document@example.com")
    db = AsyncMock()
    db.execute.return_value = FakeExecuteResult(value=document)
    repo = DocumentRepository(db)

    result = await repo.get_by_email("document@example.com")

    assert result is document
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_hashes_password_and_applies_fields(monkeypatch):
    document = SimpleNamespace(
        id=3,
        email="old@example.com",
        name="Old Name",
        password="old-hash",
        roles=[RoleOption.DOCUMENT],
    )
    db = AsyncMock()
    repo = DocumentRepository(db)
    payload = UpdateDocumentRequest(
        email="new@example.com",
        password="new-password",
        roles=[RoleOption.ADMIN],
    )

    monkeypatch.setattr(
        "app.repositories.document_repository.hash_password",
        lambda password: f"hashed::{password}",
    )
    repo.get_by_id = AsyncMock(return_value=document)

    result = await repo.update(3, payload)

    assert result is document
    assert document.email == "new@example.com"
    assert document.password == "hashed::new-password"
    assert document.roles == [RoleOption.ADMIN]


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