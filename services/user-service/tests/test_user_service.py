from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.dto.user_dto import CreateUserRequest, UpdateUserRequest
from app.events.user_events import UserCreatedEvent, UserDeletedEvent, UserUpdatedEvent
from app.models.user import RoleOption
from app.services.user_service import UserService


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


def make_user(user_id=1, email="user@example.com", name="User", roles=None):
    return SimpleNamespace(
        id=user_id,
        email=email,
        name=name,
        password="hashed-password",
        roles=roles or [RoleOption.USER],
    )


@pytest.mark.asyncio
async def test_get_users_maps_entities_to_responses():
    repo = SimpleNamespace(get_all=AsyncMock(return_value=[make_user(), make_user(2)]))
    producer = SimpleNamespace()
    service = UserService(FakeUnitOfWork(), repo, producer)

    result = await service.get_users()

    assert [user.id for user in result] == [1, 2]
    assert all(user.email.endswith("@example.com") for user in result)


@pytest.mark.asyncio
async def test_create_user_flushes_and_publishes_created_event():
    user = make_user()
    uow = FakeUnitOfWork()
    repo = SimpleNamespace(create=AsyncMock(return_value=user))
    producer = SimpleNamespace(user_created=AsyncMock())
    service = UserService(uow, repo, producer)
    payload = CreateUserRequest(
        email="user@example.com",
        name="User",
        password="secret",
        roles=[RoleOption.USER],
    )

    result = await service.create_user(payload)

    repo.create.assert_awaited_once_with(payload)
    uow.session.flush.assert_awaited_once()
    producer.user_created.assert_awaited_once()
    event = producer.user_created.await_args.args[0]
    assert isinstance(event, UserCreatedEvent)
    assert event.id == user.id
    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_user_by_id_returns_none_when_missing():
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    service = UserService(FakeUnitOfWork(), repo, SimpleNamespace())

    result = await service.get_user_by_id(404)

    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_id_maps_model_to_response():
    user = make_user(8)
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    service = UserService(FakeUnitOfWork(), repo, SimpleNamespace())

    result = await service.get_user_by_id(8)

    assert result is not None
    assert result.id == 8
    assert result.email == user.email


@pytest.mark.asyncio
async def test_update_user_publishes_updated_fields():
    user = make_user(9, name="Updated User")
    uow = FakeUnitOfWork()
    repo = SimpleNamespace(update=AsyncMock(return_value=user))
    producer = SimpleNamespace(user_updated=AsyncMock())
    service = UserService(uow, repo, producer)
    payload = UpdateUserRequest(name="Updated User", password="new-secret")

    result = await service.update_user(9, payload)

    repo.update.assert_awaited_once_with(9, payload)
    producer.user_updated.assert_awaited_once()
    event = producer.user_updated.await_args.args[0]
    assert isinstance(event, UserUpdatedEvent)
    assert event.updated == ["name", "password"]
    assert result is not None
    assert result.id == 9


@pytest.mark.asyncio
async def test_update_user_returns_none_without_event_when_missing():
    repo = SimpleNamespace(update=AsyncMock(return_value=None))
    producer = SimpleNamespace(user_updated=AsyncMock())
    service = UserService(FakeUnitOfWork(), repo, producer)

    result = await service.update_user(404, UpdateUserRequest(name="Missing"))

    assert result is None
    producer.user_updated.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_user_publishes_deleted_event():
    user = make_user(12)
    repo = SimpleNamespace(delete=AsyncMock(return_value=user))
    producer = SimpleNamespace(user_deleted=AsyncMock())
    service = UserService(FakeUnitOfWork(), repo, producer)

    result = await service.delete_user(12)

    producer.user_deleted.assert_awaited_once()
    event = producer.user_deleted.await_args.args[0]
    assert isinstance(event, UserDeletedEvent)
    assert event.id == 12
    assert result is not None
    assert result.id == 12


@pytest.mark.asyncio
async def test_delete_user_returns_none_without_event_when_missing():
    repo = SimpleNamespace(delete=AsyncMock(return_value=None))
    producer = SimpleNamespace(user_deleted=AsyncMock())
    service = UserService(FakeUnitOfWork(), repo, producer)

    result = await service.delete_user(77)

    assert result is None
    producer.user_deleted.assert_not_awaited()