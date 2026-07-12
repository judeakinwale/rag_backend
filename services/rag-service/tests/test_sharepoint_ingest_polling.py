import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.core import lifespan as lifespan_module
from app.scheduler.polling import LOCK_KEY, SharePointIngestPoller


class FakeSessionFactory:
    def __init__(self, session):
        self.session = session
        self.entered = 0
        self.exited = 0

    def __call__(self):
        return self

    async def __aenter__(self):
        self.entered += 1
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited += 1


def build_poller(*, redis_client=None, container_obj=None, session_factory=None, settings_obj=None, sleep_func=None):
    redis_client = redis_client or SimpleNamespace(
        acquire_lock=AsyncMock(return_value="token-1"),
        release_lock=AsyncMock(return_value=True),
    )
    ingest_service = SimpleNamespace(start_sharepoint_ingest=AsyncMock())
    container_obj = container_obj or SimpleNamespace(
        document_service=MagicMock(return_value="document-service"),
        ingest_service=MagicMock(return_value=ingest_service),
    )
    session_factory = session_factory or FakeSessionFactory(SimpleNamespace())
    settings_obj = settings_obj or SimpleNamespace(
        SHAREPOINT_INGEST_POLL_ENABLED=True,
        SHAREPOINT_INGEST_POLL_INTERVAL_SECONDS=300,
        SHAREPOINT_INGEST_LOCK_TTL_SECONDS=600,
        SHAREPOINT_LIBRARY_IDS=None,
    )
    sleep_func = sleep_func or AsyncMock()

    poller = SharePointIngestPoller(
        kafka_producer=SimpleNamespace(),
        sharepoint_service=SimpleNamespace(),
        settings_obj=settings_obj,
        redis_client=redis_client,
        container_obj=container_obj,
        session_factory=session_factory,
        sleep_func=sleep_func,
    )
    return poller, redis_client, container_obj, session_factory, ingest_service


@pytest.mark.asyncio
async def test_poll_once_acquires_lock_before_calling_ingest():
    order = []
    redis_client = SimpleNamespace(
        acquire_lock=AsyncMock(side_effect=lambda *args, **kwargs: order.append("lock") or "token-1"),
        release_lock=AsyncMock(side_effect=lambda *args, **kwargs: order.append("unlock") or True),
    )
    ingest_service = SimpleNamespace(
        start_sharepoint_ingest=AsyncMock(side_effect=lambda payload: order.append("ingest")),
    )
    container_obj = SimpleNamespace(
        document_service=MagicMock(return_value="document-service"),
        ingest_service=MagicMock(return_value=ingest_service),
    )
    poller, _, _, _, _ = build_poller(redis_client=redis_client, container_obj=container_obj)

    await poller.poll_once()

    assert order == ["lock", "ingest", "unlock"]
    redis_client.acquire_lock.assert_awaited_once_with(LOCK_KEY, 600)
    payload = ingest_service.start_sharepoint_ingest.await_args.args[0]
    assert payload.force_reprocess is False
    assert payload.force_reprocess_all is False


@pytest.mark.asyncio
async def test_poll_once_skips_ingest_when_lock_is_unavailable(caplog):
    redis_client = SimpleNamespace(
        acquire_lock=AsyncMock(return_value=None),
        release_lock=AsyncMock(return_value=True),
    )
    poller, _, container_obj, _, ingest_service = build_poller(redis_client=redis_client)

    with caplog.at_level("INFO"):
        await poller.poll_once()

    ingest_service.start_sharepoint_ingest.assert_not_awaited()
    redis_client.release_lock.assert_not_awaited()
    assert "lock" in caplog.text.lower()
    assert container_obj.document_service.call_count == 0


@pytest.mark.asyncio
async def test_poll_once_releases_lock_after_success():
    poller, redis_client, _, _, _ = build_poller()

    await poller.poll_once()

    redis_client.release_lock.assert_awaited_once_with(LOCK_KEY, "token-1")


@pytest.mark.asyncio
async def test_poll_once_releases_lock_after_failure(caplog):
    ingest_service = SimpleNamespace(
        start_sharepoint_ingest=AsyncMock(side_effect=RuntimeError("boom")),
    )
    container_obj = SimpleNamespace(
        document_service=MagicMock(return_value="document-service"),
        ingest_service=MagicMock(return_value=ingest_service),
    )
    poller, redis_client, _, _, _ = build_poller(container_obj=container_obj)

    with caplog.at_level("ERROR"):
        await poller.poll_once()

    redis_client.release_lock.assert_awaited_once_with(LOCK_KEY, "token-1")
    assert "sharepoint ingest poll failed" in caplog.text.lower()


@pytest.mark.asyncio
async def test_poll_once_skips_when_disabled():
    settings_obj = SimpleNamespace(
        SHAREPOINT_INGEST_POLL_ENABLED=False,
        SHAREPOINT_INGEST_POLL_INTERVAL_SECONDS=300,
        SHAREPOINT_INGEST_LOCK_TTL_SECONDS=600,
        SHAREPOINT_LIBRARY_IDS=None,
    )
    poller, redis_client, _, _, ingest_service = build_poller(settings_obj=settings_obj)

    await poller.poll_once()

    redis_client.acquire_lock.assert_not_awaited()
    ingest_service.start_sharepoint_ingest.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_creates_one_background_task_and_stop_cancels_cleanly():
    started = asyncio.Event()

    async def blocking_sleep(_: float):
        started.set()
        await asyncio.Future()

    poller, _, _, _, _ = build_poller(sleep_func=blocking_sleep)

    await poller.start()
    await started.wait()
    first_task = poller._task

    await poller.start()
    await poller.stop()

    assert first_task is not None
    assert poller._task is None
    assert first_task.done()


def test_settings_defaults_for_sharepoint_polling():
    settings_obj = Settings()

    assert settings_obj.SHAREPOINT_INGEST_POLL_INTERVAL_SECONDS == 300
    assert settings_obj.SHAREPOINT_INGEST_POLL_ENABLED is True
    assert settings_obj.SHAREPOINT_INGEST_LOCK_TTL_SECONDS == 600


def test_settings_parse_sharepoint_poll_library_ids_from_env(monkeypatch):
    monkeypatch.setenv("SHAREPOINT_INGEST_POLL_ENABLED", "false")
    monkeypatch.setenv("SHAREPOINT_LIBRARY_IDS", '["lib-a", "lib-b"]')

    settings_obj = Settings()

    assert settings_obj.SHAREPOINT_INGEST_POLL_ENABLED is False
    assert settings_obj.SHAREPOINT_LIBRARY_IDS == ["lib-a", "lib-b"]


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_poller_when_dependencies_are_ready(monkeypatch):
    app = FastAPI()
    kafka_producer = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())
    kafka_consumer = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())
    sharepoint_service = SimpleNamespace()
    poller = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())

    monkeypatch.setattr(lifespan_module, "KafkaProducer", MagicMock(return_value=kafka_producer))
    monkeypatch.setattr(lifespan_module, "KafkaConsumer", MagicMock(return_value=kafka_consumer))
    monkeypatch.setattr(lifespan_module, "SharepointService", MagicMock(return_value=sharepoint_service))
    poller_factory = MagicMock(return_value=poller)
    monkeypatch.setattr(lifespan_module, "SharePointIngestPoller", poller_factory)
    engine = SimpleNamespace(dispose=AsyncMock())
    redis_client = SimpleNamespace(close=AsyncMock())
    monkeypatch.setattr(lifespan_module, "engine", engine)
    monkeypatch.setattr(lifespan_module, "r", redis_client)

    async with lifespan_module.lifespan(app):
        assert app.state.sharepoint_ingest_poller is poller
        poller.start.assert_awaited_once()

    poller_factory.assert_called_once_with(
        kafka_producer=kafka_producer,
        sharepoint_service=sharepoint_service,
    )
    poller.stop.assert_awaited_once()
    kafka_producer.stop.assert_awaited_once()
    kafka_consumer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_does_not_start_poller_when_sharepoint_service_is_unavailable(monkeypatch):
    app = FastAPI()
    kafka_producer = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())
    kafka_consumer = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())

    monkeypatch.setattr(lifespan_module, "KafkaProducer", MagicMock(return_value=kafka_producer))
    monkeypatch.setattr(lifespan_module, "KafkaConsumer", MagicMock(return_value=kafka_consumer))
    monkeypatch.setattr(lifespan_module, "SharepointService", MagicMock(side_effect=RuntimeError("missing creds")))
    poller_factory = MagicMock()
    monkeypatch.setattr(lifespan_module, "SharePointIngestPoller", poller_factory)
    engine = SimpleNamespace(dispose=AsyncMock())
    redis_client = SimpleNamespace(close=AsyncMock())
    monkeypatch.setattr(lifespan_module, "engine", engine)
    monkeypatch.setattr(lifespan_module, "r", redis_client)

    async with lifespan_module.lifespan(app):
        assert app.state.sharepoint_ingest_poller is None

    poller_factory.assert_not_called()