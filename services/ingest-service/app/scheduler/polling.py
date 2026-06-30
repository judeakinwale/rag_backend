import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.config import Settings, settings
from app.core.container import Container, container
from app.core.db import async_session
from app.core.redis import r
from app.dto.ingest_dto import CreateIngestRequest
from app.services.sharepoint_service import SharepointService
from rag_packages.shared.kafka.producer import KafkaProducer


logger = logging.getLogger(__name__)

LOCK_KEY = "locks:sharepoint_ingest_poll"


class SharePointIngestPoller:
    def __init__(
        self,
        *,
        kafka_producer: KafkaProducer,
        sharepoint_service: SharepointService,
        settings_obj: Settings = settings,
        redis_client: Any = r,
        container_obj: Container = container,
        session_factory: Callable[[], Any] = async_session,
        sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
        run_on_startup: bool = False,
    ):
        self.kafka_producer = kafka_producer
        self.sharepoint_service = sharepoint_service
        self.settings = settings_obj
        self.redis_client = redis_client
        self.container = container_obj
        self.session_factory = session_factory
        self.sleep = sleep_func
        self.run_on_startup = run_on_startup
        self._task: asyncio.Task[None] | None = None

    async def poll_once(self) -> None:
        if not self.settings.SHAREPOINT_INGEST_POLL_ENABLED:
            logger.debug("SharePoint ingest polling is disabled")
            return

        token = await self.redis_client.acquire_lock(
            LOCK_KEY,
            self.settings.SHAREPOINT_INGEST_LOCK_TTL_SECONDS,
        )
        if token is None:
            logger.info(
                "SharePoint ingest poll skipped because another worker holds the lock"
            )
            return

        try:
            async with self.session_factory() as db_session:
                document_service = self.container.document_service(
                    db_session,
                    kafka_producer=self.kafka_producer,
                )
                ingest_service = self.container.ingest_service(
                    db_session,
                    kafka_producer=self.kafka_producer,
                    document_service=document_service,
                    sharepoint_service=self.sharepoint_service,
                )
                payload = CreateIngestRequest(
                    library_ids=self.settings.SHAREPOINT_INGEST_POLL_LIBRARY_IDS,
                    force_reprocess=False,
                    force_reprocess_all=False,
                )
                await ingest_service.start_sharepoint_ingest(payload)

        except Exception:
            logger.exception("SharePoint ingest poll failed")

        finally:
            released = await self.redis_client.release_lock(LOCK_KEY, token)
            if not released:
                logger.warning("SharePoint ingest poll lock was not released cleanly")

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return

        self._task = asyncio.create_task(
            self._run_loop(),
            name="sharepoint-ingest-poller",
        )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _run_loop(self) -> None:
        if self.run_on_startup:
            await self.poll_once()

        while True:
            print(f"Sleeping for {self.settings.SHAREPOINT_INGEST_POLL_INTERVAL_SECONDS} seconds before next poll")
        
            await self.sleep(self.settings.SHAREPOINT_INGEST_POLL_INTERVAL_SECONDS)
            await self.poll_once()
