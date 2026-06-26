from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.dto.ingest_dto import CreateIngestRequest, UpdateIngestRequest
from app.models.ingest import RoleOption
from app.repositories.ingest_repository import IngestRepository


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
    ingests = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    db = AsyncMock()
    db.execute.return_value = FakeExecuteResult(values=ingests)
    repo = IngestRepository(db)

    result = await repo.get_all()

    assert result == ingests
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_hashes_password(monkeypatch):
    db = SimpleNamespace(add=Mock())
    repo = IngestRepository(db)
    payload = CreateIngestRequest(
        email="ingest@example.com",
        name="Test Ingest",
        password="plain-text",
        roles=[RoleOption.ADMIN],
    )

    monkeypatch.setattr(
        "app.repositories.ingest_repository.hash_password",
        lambda password: f"hashed::{password}",
    )

    ingest = await repo.create(payload)

    assert ingest.email == payload.email
    assert ingest.name == payload.name
    assert ingest.password == "hashed::plain-text"
    assert ingest.roles == [RoleOption.ADMIN]
    db.add.assert_called_once_with(ingest)


@pytest.mark.asyncio
async def test_get_by_id_uses_session_get():
    ingest = SimpleNamespace(id=10)
    db = AsyncMock()
    db.get.return_value = ingest
    repo = IngestRepository(db)

    result = await repo.get_by_id(10)

    assert result is ingest
    db.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_email_returns_single_ingest():
    ingest = SimpleNamespace(id=7, email="ingest@example.com")
    db = AsyncMock()
    db.execute.return_value = FakeExecuteResult(value=ingest)
    repo = IngestRepository(db)

    result = await repo.get_by_email("ingest@example.com")

    assert result is ingest
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_hashes_password_and_applies_fields(monkeypatch):
    ingest = SimpleNamespace(
        id=3,
        email="old@example.com",
        name="Old Name",
        password="old-hash",
        roles=[RoleOption.INGEST],
    )
    db = AsyncMock()
    repo = IngestRepository(db)
    payload = UpdateIngestRequest(
        email="new@example.com",
        password="new-password",
        roles=[RoleOption.ADMIN],
    )

    monkeypatch.setattr(
        "app.repositories.ingest_repository.hash_password",
        lambda password: f"hashed::{password}",
    )
    repo.get_by_id = AsyncMock(return_value=ingest)

    result = await repo.update(3, payload)

    assert result is ingest
    assert ingest.email == "new@example.com"
    assert ingest.password == "hashed::new-password"
    assert ingest.roles == [RoleOption.ADMIN]


@pytest.mark.asyncio
async def test_update_returns_none_when_ingest_missing():
    db = AsyncMock()
    repo = IngestRepository(db)
    repo.get_by_id = AsyncMock(return_value=None)

    result = await repo.update(999, UpdateIngestRequest(name="Missing"))

    assert result is None


@pytest.mark.asyncio
async def test_delete_removes_existing_ingest():
    ingest = SimpleNamespace(id=5)
    db = AsyncMock()
    repo = IngestRepository(db)
    repo.get_by_id = AsyncMock(return_value=ingest)

    result = await repo.delete(5)

    assert result is ingest
    db.delete.assert_awaited_once_with(ingest)


@pytest.mark.asyncio
async def test_delete_returns_none_when_ingest_missing():
    db = AsyncMock()
    repo = IngestRepository(db)
    repo.get_by_id = AsyncMock(return_value=None)

    result = await repo.delete(123)

    assert result is None
    db.delete.assert_not_called()