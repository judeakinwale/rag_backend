from types import SimpleNamespace

from fastapi import FastAPI
from starlette.requests import Request

from app.core.container import Container
from app.dependencies import document as document_dependencies
from app.dependencies import ingest as ingest_dependencies
from app.producers.document_producer import DocumentProducer
from app.producers.ingest_producer import IngestProducer
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.services.ingest_service import IngestService
from rag_packages.shared.database.uow import UnitOfWork


def test_container_creates_document_repository_with_db_session():
    container = Container()
    db = SimpleNamespace()

    repo = container.document_repository(db)

    assert isinstance(repo, DocumentRepository)
    assert repo.db is db


def test_container_creates_document_producer_with_kafka_producer():
    container = Container()
    kafka_producer = SimpleNamespace()

    producer = container.document_producer(kafka_producer)

    assert isinstance(producer, DocumentProducer)
    assert producer.producer is kafka_producer


def test_container_creates_document_service_with_explicit_document_producer():
    container = Container()
    db = SimpleNamespace()
    producer = SimpleNamespace()

    service = container.document_service(db, document_producer=producer)

    assert isinstance(service, DocumentService)
    assert isinstance(service.uow, UnitOfWork)
    assert service.uow.session is db
    assert isinstance(service.repo, DocumentRepository)
    assert service.repo.db is db
    assert service.producer is producer


def test_container_creates_ingest_producer_with_kafka_producer():
    container = Container()
    kafka_producer = SimpleNamespace()

    producer = container.ingest_producer(kafka_producer)

    assert isinstance(producer, IngestProducer)
    assert producer.producer is kafka_producer


def test_container_creates_ingest_service_with_explicit_dependencies():
    container = Container()
    db = SimpleNamespace()
    producer = SimpleNamespace()
    document_service = SimpleNamespace()
    sharepoint_service = SimpleNamespace()

    service = container.ingest_service(
        db,
        ingest_producer=producer,
        document_service=document_service,
        sharepoint_service=sharepoint_service,
    )

    assert isinstance(service, IngestService)
    assert isinstance(service.uow, UnitOfWork)
    assert service.uow.session is db
    assert isinstance(service.doc_repo, DocumentRepository)
    assert service.doc_repo.db is db
    assert service.producer is producer
    assert service.document_service is document_service
    assert service.sharepoint_service is sharepoint_service
    assert service.document_source == "sharepoint"


def test_get_document_producer_uses_request_app_state():
    kafka_producer = SimpleNamespace()
    app = FastAPI()
    app.state.kafka_producer = kafka_producer
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "app": app,
        }
    )

    producer = document_dependencies.get_document_producer(request)

    assert isinstance(producer, DocumentProducer)
    assert producer.producer is kafka_producer


def test_get_document_repository_uses_container_factory(monkeypatch):
    db = SimpleNamespace()
    sentinel = object()
    calls = []

    def fake_document_repository(arg):
        calls.append(arg)
        return sentinel

    monkeypatch.setattr(document_dependencies.container, "document_repository", fake_document_repository)

    repo = document_dependencies.get_document_repository(db)

    assert repo is sentinel
    assert calls == [db]


def test_get_document_service_uses_container_factory(monkeypatch):
    db = SimpleNamespace()
    producer = SimpleNamespace()
    sentinel = object()
    calls = []

    def fake_document_service(arg_db, document_producer=None, kafka_producer=None):
        calls.append((arg_db, document_producer, kafka_producer))
        return sentinel

    monkeypatch.setattr(document_dependencies.container, "document_service", fake_document_service)

    service = document_dependencies.get_document_service(db, producer)

    assert service is sentinel
    assert calls == [(db, producer, None)]


def test_get_ingest_producer_uses_request_app_state():
    kafka_producer = SimpleNamespace()
    app = FastAPI()
    app.state.kafka_producer = kafka_producer
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "app": app,
        }
    )

    producer = ingest_dependencies.get_ingest_producer(request)

    assert isinstance(producer, IngestProducer)
    assert producer.producer is kafka_producer


def test_get_sharepoint_service_uses_request_app_state():
    sharepoint_service = SimpleNamespace()
    app = FastAPI()
    app.state.sharepoint_service = sharepoint_service
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "app": app,
        }
    )

    service = ingest_dependencies.get_sharepoint_service(request)

    assert service is sharepoint_service


def test_get_ingest_service_uses_container_factory(monkeypatch):
    db = SimpleNamespace()
    producer = SimpleNamespace()
    document_service = SimpleNamespace()
    sharepoint_service = SimpleNamespace()
    sentinel = object()
    calls = []

    def fake_ingest_service(
        arg_db,
        ingest_producer=None,
        kafka_producer=None,
        document_service=None,
        sharepoint_service=None,
    ):
        calls.append(
            (
                arg_db,
                ingest_producer,
                kafka_producer,
                document_service,
                sharepoint_service,
            )
        )
        return sentinel

    monkeypatch.setattr(ingest_dependencies.container, "ingest_service", fake_ingest_service)

    service = ingest_dependencies.get_ingest_service(
        db,
        producer,
        document_service,
        sharepoint_service,
    )

    assert service is sentinel
    assert calls == [
        (db, producer, None, document_service, sharepoint_service)
    ]
