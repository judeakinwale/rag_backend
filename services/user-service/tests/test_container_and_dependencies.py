from types import SimpleNamespace

from fastapi import FastAPI
from starlette.requests import Request

from app.core.container import Container
from app.dependencies import user as user_dependencies
from app.producers.user_producer import UserProducer
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from rag_packages.shared.database.uow import UnitOfWork


def test_container_creates_repository_with_db_session():
    container = Container()
    db = SimpleNamespace()

    repo = container.user_repository(db)

    assert isinstance(repo, UserRepository)
    assert repo.db is db


def test_container_creates_user_producer_with_kafka_producer():
    container = Container()
    kafka_producer = SimpleNamespace()

    producer = container.user_producer(kafka_producer)

    assert isinstance(producer, UserProducer)
    assert producer.producer is kafka_producer


def test_container_creates_user_service_with_explicit_user_producer():
    container = Container()
    db = SimpleNamespace()
    producer = SimpleNamespace()

    service = container.user_service(db, user_producer=producer)

    assert isinstance(service, UserService)
    assert isinstance(service.uow, UnitOfWork)
    assert service.uow.session is db
    assert isinstance(service.repo, UserRepository)
    assert service.repo.db is db
    assert service.producer is producer


def test_container_creates_user_service_from_kafka_producer_when_needed():
    container = Container()
    db = SimpleNamespace()
    kafka_producer = SimpleNamespace()

    service = container.user_service(db, kafka_producer=kafka_producer)

    assert isinstance(service, UserService)
    assert isinstance(service.producer, UserProducer)
    assert service.producer.producer is kafka_producer


def test_get_user_producer_uses_request_app_state():
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

    producer = user_dependencies.get_user_producer(request)

    assert isinstance(producer, UserProducer)
    assert producer.producer is kafka_producer


def test_get_user_repository_uses_container_factory(monkeypatch):
    db = SimpleNamespace()
    sentinel = object()
    calls = []

    def fake_user_repository(arg):
        calls.append(arg)
        return sentinel

    monkeypatch.setattr(user_dependencies.container, "user_repository", fake_user_repository)

    repo = user_dependencies.get_user_repository(db)

    assert repo is sentinel
    assert calls == [db]


def test_get_user_service_uses_container_factory(monkeypatch):
    db = SimpleNamespace()
    producer = SimpleNamespace()
    sentinel = object()
    calls = []

    def fake_user_service(arg_db, user_producer=None, kafka_producer=None):
        calls.append((arg_db, user_producer, kafka_producer))
        return sentinel

    monkeypatch.setattr(user_dependencies.container, "user_service", fake_user_service)

    service = user_dependencies.get_user_service(db, producer)

    assert service is sentinel
    assert calls == [(db, producer, None)]