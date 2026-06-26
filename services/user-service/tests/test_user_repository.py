from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.dto.user_dto import CreateUserRequest, UpdateUserRequest
from app.models.user import RoleOption
from app.repositories.user_repository import UserRepository


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
    users = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    db = AsyncMock()
    db.execute.return_value = FakeExecuteResult(values=users)
    repo = UserRepository(db)

    result = await repo.get_all()

    assert result == users
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_hashes_password(monkeypatch):
    db = SimpleNamespace(add=Mock())
    repo = UserRepository(db)
    payload = CreateUserRequest(
        email="user@example.com",
        name="Test User",
        password="plain-text",
        roles=[RoleOption.ADMIN],
    )

    monkeypatch.setattr(
        "app.repositories.user_repository.hash_password",
        lambda password: f"hashed::{password}",
    )

    user = await repo.create(payload)

    assert user.email == payload.email
    assert user.name == payload.name
    assert user.password == "hashed::plain-text"
    assert user.roles == [RoleOption.ADMIN]
    db.add.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_get_by_id_uses_session_get():
    user = SimpleNamespace(id=10)
    db = AsyncMock()
    db.get.return_value = user
    repo = UserRepository(db)

    result = await repo.get_by_id(10)

    assert result is user
    db.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_email_returns_single_user():
    user = SimpleNamespace(id=7, email="user@example.com")
    db = AsyncMock()
    db.execute.return_value = FakeExecuteResult(value=user)
    repo = UserRepository(db)

    result = await repo.get_by_email("user@example.com")

    assert result is user
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_hashes_password_and_applies_fields(monkeypatch):
    user = SimpleNamespace(
        id=3,
        email="old@example.com",
        name="Old Name",
        password="old-hash",
        roles=[RoleOption.USER],
    )
    db = AsyncMock()
    repo = UserRepository(db)
    payload = UpdateUserRequest(
        email="new@example.com",
        password="new-password",
        roles=[RoleOption.ADMIN],
    )

    monkeypatch.setattr(
        "app.repositories.user_repository.hash_password",
        lambda password: f"hashed::{password}",
    )
    repo.get_by_id = AsyncMock(return_value=user)

    result = await repo.update(3, payload)

    assert result is user
    assert user.email == "new@example.com"
    assert user.password == "hashed::new-password"
    assert user.roles == [RoleOption.ADMIN]


@pytest.mark.asyncio
async def test_update_returns_none_when_user_missing():
    db = AsyncMock()
    repo = UserRepository(db)
    repo.get_by_id = AsyncMock(return_value=None)

    result = await repo.update(999, UpdateUserRequest(name="Missing"))

    assert result is None


@pytest.mark.asyncio
async def test_delete_removes_existing_user():
    user = SimpleNamespace(id=5)
    db = AsyncMock()
    repo = UserRepository(db)
    repo.get_by_id = AsyncMock(return_value=user)

    result = await repo.delete(5)

    assert result is user
    db.delete.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_delete_returns_none_when_user_missing():
    db = AsyncMock()
    repo = UserRepository(db)
    repo.get_by_id = AsyncMock(return_value=None)

    result = await repo.delete(123)

    assert result is None
    db.delete.assert_not_called()