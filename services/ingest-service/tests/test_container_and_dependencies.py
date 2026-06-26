from types import SimpleNamespace

from fastapi import FastAPI
from starlette.requests import Request

from app.core.container import Container
from app.dependencies import ingest as ingest_dependencies
from app.producers.ingest_producer import IngestProducer
from app.repositories.ingest_repository import IngestRepository
from app.services.ingest_service import IngestService
from rag_packages.shared.database.uow import UnitOfWork


def test_container_creates_repository_with_db_session():
    container = Container()
    db = SimpleNamespace()

    repo = container.ingest_repository(db)

    assert isinstance(repo, IngestRepository)
    assert repo.db is db


def test_container_creates_ingest_producer_with_kafka_producer():
    container = Container()
    kafka_producer = SimpleNamespace()

    producer = container.ingest_producer(kafka_producer)

    assert isinstance(producer, IngestProducer)
    assert producer.producer is kafka_producer


def test_container_creates_ingest_service_with_explicit_ingest_producer():
    container = Container()
    db = SimpleNamespace()
    producer = SimpleNamespace()

    service = container.ingest_service(db, ingest_producer=producer)

    assert isinstance(service, IngestService)
    assert isinstance(service.uow, UnitOfWork)
    assert service.uow.session is db
    assert isinstance(service.repo, IngestRepository)
    assert service.repo.db is db
    assert service.producer is producer


def test_container_creates_ingest_service_from_kafka_producer_when_needed():
    container = Container()
    db = SimpleNamespace()
    kafka_producer = SimpleNamespace()

    service = container.ingest_service(db, kafka_producer=kafka_producer)

    assert isinstance(service, IngestService)
    assert isinstance(service.producer, IngestProducer)
    assert service.producer.producer is kafka_producer


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


def test_get_ingest_repository_uses_container_factory(monkeypatch):
    db = SimpleNamespace()
    sentinel = object()
    calls = []

    def fake_ingest_repository(arg):
        calls.append(arg)
        return sentinel

    monkeypatch.setattr(ingest_dependencies.container, "ingest_repository", fake_ingest_repository)

    repo = ingest_dependencies.get_ingest_repository(db)

    assert repo is sentinel
    assert calls == [db]


def test_get_ingest_service_uses_container_factory(monkeypatch):
    db = SimpleNamespace()
    producer = SimpleNamespace()
    sentinel = object()
    calls = []

    def fake_ingest_service(arg_db, ingest_producer=None, kafka_producer=None):
        calls.append((arg_db, ingest_producer, kafka_producer))
        return sentinel

    monkeypatch.setattr(ingest_dependencies.container, "ingest_service", fake_ingest_service)

    service = ingest_dependencies.get_ingest_service(db, producer)

    assert service is sentinel
    assert calls == [(db, producer, None)]