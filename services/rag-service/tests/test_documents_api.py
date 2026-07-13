from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.documents import router
from app.dependencies.document import get_document_service
from app.dependencies.ingest import get_sharepoint_service
from rag_packages.contracts.dto.document import DocumentResponse


TIMESTAMP = datetime(2024, 1, 1, tzinfo=UTC)
def make_document_response(document_id=1, **overrides):
    payload = {
        "id": document_id,
        "name": f"Document {document_id}",
        "file_url": f"https://contoso.example/docs/{document_id}.pdf",
        "library_name": "Shared Documents",
        "library_id": "library-1",
        "site_url": "https://contoso.sharepoint.com/sites/demo",
        "parent_folder_path": "/general",
        "source": "sharepoint",
        "file_metadata": {"etag": f"etag-{document_id}"},
        "last_modified": TIMESTAMP,
        "file_type": "pdf",
        "file_size": 1024,
        "ingest_initiated_at": TIMESTAMP,
        "ingest_status": "started",
        "prev_batch_ingest_init": None,
        "created_at": TIMESTAMP,
        "created_by_id": None,
        "updated_at": TIMESTAMP,
        "updated_by_id": None,
        "is_active": True,
        "is_deleted": False,
    }
    payload.update(overrides)
    return DocumentResponse(**payload)


def build_app(service, sharepoint_service=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_document_service] = lambda: service
    app.dependency_overrides[get_sharepoint_service] = lambda: sharepoint_service
    return app


def test_get_documents_returns_payload_and_count():
    service = type("Service", (), {})()
    service.get_documents = AsyncMock(
        return_value=([make_document_response(1)], 1)
    )

    client = TestClient(build_app(service))
    response = client.get("/api/v1/documents?page=1&size=10")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": [
            {
                "id": 1,
                "name": "Document 1",
                "file_url": "https://contoso.example/docs/1.pdf",
                "library_name": "Shared Documents",
                "library_id": "library-1",
                "site_url": "https://contoso.sharepoint.com/sites/demo",
                "parent_folder_path": "/general",
                "source": "sharepoint",
                "file_metadata": {"etag": "etag-1"},
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
        ],
        "count": 1,
    }


def test_create_document_returns_created_document():
    created_document = make_document_response(2)
    service = type("Service", (), {})()
    service.create_document = AsyncMock(return_value=created_document)

    client = TestClient(build_app(service))
    response = client.post(
        "/api/v1/documents",
        json={
            "name": "Document 2",
            "file_url": "https://contoso.example/docs/2.pdf",
            "library_name": "Shared Documents",
            "library_id": "library-1",
            "site_url": "https://contoso.sharepoint.com/sites/demo",
            "parent_folder_path": "/general",
            "source": "sharepoint",
            "file_metadata": {"etag": "etag-2"},
            "last_modified": "2024-01-01T00:00:00Z",
            "file_type": "pdf",
            "file_size": 1024,
        },
    )

    assert response.status_code == 201
    assert response.json()["data"]["id"] == 2
    assert response.json()["data"]["source"] == "sharepoint"


def test_get_document_returns_single_document_payload():
    service = type("Service", (), {})()
    service.get_document_by_id = AsyncMock(return_value=make_document_response(5))

    client = TestClient(build_app(service, sharepoint_service=type("SharePoint", (), {})()))
    response = client.get("/api/v1/documents/5")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == 5


def test_get_document_with_include_file_enriches_response():
    service = type("Service", (), {})()
    service.get_document_by_id = AsyncMock(return_value=make_document_response(6))
    sharepoint_service = type("SharePoint", (), {})()
    sharepoint_service.get_file = AsyncMock(
        return_value={"b64": "ZmFrZQ==", "size": 2048, "sha256": "abc123"}
    )

    client = TestClient(build_app(service, sharepoint_service=sharepoint_service))
    response = client.get("/api/v1/documents/6?include_file=true")

    assert response.status_code == 200
    assert response.json()["data"]["file_b64"] == "ZmFrZQ=="
    assert response.json()["data"]["file_size"] == 2048
    assert response.json()["data"]["file_sha256"] == "abc123"
    sharepoint_service.get_file.assert_awaited_once_with(
        "https://contoso.example/docs/6.pdf"
    )


def test_update_document_returns_updated_payload_for_put_and_patch():
    updated_document = make_document_response(8, name="Updated Document", ingest_status="processing")

    for method in ("put", "patch"):
        service = type("Service", (), {})()
        service.update_document = AsyncMock(return_value=updated_document)
        client = TestClient(build_app(service))

        response = getattr(client, method)(
            "/api/v1/documents/8",
            json={"name": "Updated Document", "ingest_status": "processing"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["id"] == 8
        assert response.json()["data"]["ingest_status"] == "processing"


def test_delete_document_returns_deleted_payload_and_message():
    service = type("Service", (), {})()
    service.delete_document = AsyncMock(return_value=make_document_response(10))

    client = TestClient(build_app(service))
    response = client.delete("/api/v1/documents/10")

    assert response.status_code == 200
    assert response.json()["message"] == "Document with ID 10 has been deleted."
    assert response.json()["data"]["id"] == 10
