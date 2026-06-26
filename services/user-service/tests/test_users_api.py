from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.users import router
from app.dependencies.user import get_user_producer, get_user_service
from app.dto.user_dto import UserResponse
from app.models.user import RoleOption


def build_app(service, producer) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_user_service] = lambda: service
    app.dependency_overrides[get_user_producer] = lambda: producer
    return app


def test_get_users_returns_payload_and_emits_probe_event():
    service = type("Service", (), {})()
    service.get_users = AsyncMock(
        return_value=[
            UserResponse(
                id=1,
                email="user@example.com",
                name="User",
                roles=[RoleOption.USER],
            )
        ]
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.get("/api/v1/users")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": [
            {
                "id": 1,
                "email": "user@example.com",
                "name": "User",
                "roles": ["user"],
            }
        ],
    }
    producer.test.assert_awaited_once_with({"event_msg": "get_users_called"})


def test_create_user_returns_created_user():
    created_user = UserResponse(
        id=2,
        email="created@example.com",
        name="Created",
        roles=[RoleOption.ADMIN],
    )
    service = type("Service", (), {})()
    service.create_user = AsyncMock(return_value=created_user)
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.post(
        "/api/v1/users",
        json={
            "email": "created@example.com",
            "name": "Created",
            "password": "secret",
            "roles": ["admin"],
        },
    )

    assert response.status_code == 201
    assert response.json()["data"] == {
        "id": 2,
        "email": "created@example.com",
        "name": "Created",
        "roles": ["admin"],
    }


def test_get_user_returns_single_user_payload():
    service = type("Service", (), {})()
    service.get_user_by_id = AsyncMock(
        return_value=UserResponse(
            id=5,
            email="user5@example.com",
            name="User Five",
            roles=[RoleOption.USER],
        )
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.get("/api/v1/users/5")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == 5


def test_update_user_returns_updated_payload_for_put_and_patch():
    updated_user = UserResponse(
        id=8,
        email="updated@example.com",
        name="Updated",
        roles=[RoleOption.SUPERADMIN],
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    for method in ("put", "patch"):
        service = type("Service", (), {})()
        service.update_user = AsyncMock(return_value=updated_user)
        client = TestClient(build_app(service, producer))

        response = getattr(client, method)(
            "/api/v1/users/8",
            json={"name": "Updated", "roles": ["superadmin"]},
        )

        assert response.status_code == 200
        assert response.json()["data"] == {
            "id": 8,
            "email": "updated@example.com",
            "name": "Updated",
            "roles": ["superadmin"],
        }


def test_delete_user_returns_deleted_payload_and_message():
    service = type("Service", (), {})()
    service.delete_user = AsyncMock(
        return_value=UserResponse(
            id=10,
            email="deleted@example.com",
            name="Deleted",
            roles=[RoleOption.USER],
        )
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.delete("/api/v1/users/10")

    assert response.status_code == 200
    assert response.json()["message"] == "User with ID 10 has been deleted."
    assert response.json()["data"]["id"] == 10