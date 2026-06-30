from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.documents import router
from app.dependencies.document import get_document_producer, get_document_service
from app.dto.document_dto import DocumentResponse
from app.models.document import RoleOption


def build_app(service, producer) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_document_service] = lambda: service
    app.dependency_overrides[get_document_producer] = lambda: producer
    return app


def test_get_documents_returns_payload_and_emits_probe_event():
    service = type("Service", (), {})()
    service.get_documents = AsyncMock(
        return_value=[
            DocumentResponse(
                id=1,
                email="document@example.com",
                name="Document",
                roles=[RoleOption.DOCUMENT],
            )
        ]
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.get("/api/v1/documents")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": [
            {
                "id": 1,
                "email": "document@example.com",
                "name": "Document",
                "roles": ["document"],
            }
        ],
    }
    producer.test.assert_awaited_once_with({"event_msg": "get_documents_called"})


def test_create_document_returns_created_document():
    created_document = DocumentResponse(
        id=2,
        email="created@example.com",
        name="Created",
        roles=[RoleOption.ADMIN],
    )
    service = type("Service", (), {})()
    service.create_document = AsyncMock(return_value=created_document)
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.post(
        "/api/v1/documents",
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


def test_get_document_returns_single_document_payload():
    service = type("Service", (), {})()
    service.get_document_by_id = AsyncMock(
        return_value=DocumentResponse(
            id=5,
            email="document5@example.com",
            name="Document Five",
            roles=[RoleOption.DOCUMENT],
        )
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.get("/api/v1/documents/5")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == 5


def test_update_document_returns_updated_payload_for_put_and_patch():
    updated_document = DocumentResponse(
        id=8,
        email="updated@example.com",
        name="Updated",
        roles=[RoleOption.SUPERADMIN],
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    for method in ("put", "patch"):
        service = type("Service", (), {})()
        service.update_document = AsyncMock(return_value=updated_document)
        client = TestClient(build_app(service, producer))

        response = getattr(client, method)(
            "/api/v1/documents/8",
            json={"name": "Updated", "roles": ["superadmin"]},
        )

        assert response.status_code == 200
        assert response.json()["data"] == {
            "id": 8,
            "email": "updated@example.com",
            "name": "Updated",
            "roles": ["superadmin"],
        }


def test_delete_document_returns_deleted_payload_and_message():
    service = type("Service", (), {})()
    service.delete_document = AsyncMock(
        return_value=DocumentResponse(
            id=10,
            email="deleted@example.com",
            name="Deleted",
            roles=[RoleOption.DOCUMENT],
        )
    )
    producer = type("Producer", (), {})()
    producer.test = AsyncMock()

    client = TestClient(build_app(service, producer))
    response = client.delete("/api/v1/documents/10")

    assert response.status_code == 200
    assert response.json()["message"] == "Document with ID 10 has been deleted."
    assert response.json()["data"]["id"] == 10
