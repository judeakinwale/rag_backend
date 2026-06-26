from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.ingest import router
from app.dependencies.ingest import get_ingest_producer, get_ingest_service
from app.dto.ingest_dto import IngestResponse
from app.models.ingest import RoleOption


def build_app(service, producer) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_ingest_service] = lambda: service
    app.dependency_overrides[get_ingest_producer] = lambda: producer
    return app


def test_get_ingests_returns_payload_and_emits_probe_event():
    service = type("Service", (), {})()
    service.get_ingests = AsyncMock(
        return_value=[
            IngestResponse(
                id=1,
                email="ingest@example.com",
                name="Ingest",
                roles=[RoleOption.INGEST],
            )
        ]
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.get("/api/v1/ingests")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": [
            {
                "id": 1,
                "email": "ingest@example.com",
                "name": "Ingest",
                "roles": ["ingest"],
            }
        ],
    }
    producer.test.assert_awaited_once_with({"event_msg": "get_ingests_called"})


def test_create_ingest_returns_created_ingest():
    created_ingest = IngestResponse(
        id=2,
        email="created@example.com",
        name="Created",
        roles=[RoleOption.ADMIN],
    )
    service = type("Service", (), {})()
    service.create_ingest = AsyncMock(return_value=created_ingest)
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.post(
        "/api/v1/ingests",
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


def test_get_ingest_returns_single_ingest_payload():
    service = type("Service", (), {})()
    service.get_ingest_by_id = AsyncMock(
        return_value=IngestResponse(
            id=5,
            email="ingest5@example.com",
            name="Ingest Five",
            roles=[RoleOption.INGEST],
        )
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.get("/api/v1/ingests/5")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == 5


def test_update_ingest_returns_updated_payload_for_put_and_patch():
    updated_ingest = IngestResponse(
        id=8,
        email="updated@example.com",
        name="Updated",
        roles=[RoleOption.SUPERADMIN],
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    for method in ("put", "patch"):
        service = type("Service", (), {})()
        service.update_ingest = AsyncMock(return_value=updated_ingest)
        client = TestClient(build_app(service, producer))

        response = getattr(client, method)(
            "/api/v1/ingests/8",
            json={"name": "Updated", "roles": ["superadmin"]},
        )

        assert response.status_code == 200
        assert response.json()["data"] == {
            "id": 8,
            "email": "updated@example.com",
            "name": "Updated",
            "roles": ["superadmin"],
        }


def test_delete_ingest_returns_deleted_payload_and_message():
    service = type("Service", (), {})()
    service.delete_ingest = AsyncMock(
        return_value=IngestResponse(
            id=10,
            email="deleted@example.com",
            name="Deleted",
            roles=[RoleOption.INGEST],
        )
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.delete("/api/v1/ingests/10")

    assert response.status_code == 200
    assert response.json()["message"] == "Ingest with ID 10 has been deleted."
    assert response.json()["data"]["id"] == 10
