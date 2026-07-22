import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles

from app.core.lifespan import lifespan
from app.core.config import settings

# from app.api.v1.vector_documents import router as vector_documents_router_v1
from app.api.v1.ingest_overrides import router as ingest_overrides_router_v1

from rag_packages.shared.middleware.request_id import RequestIdMiddleware
from rag_packages.shared.logging.middleware import LoggingMiddleware
from rag_packages.shared.exception.exception_handler import register_exception_handlers
from rag_packages.shared.logging.packages import enable_package_logging
from rag_packages.shared.logging.config import setup_logging
from rag_packages.shared.kafka.producer import KafkaProducer


setup_logging(logging.INFO)
enable_package_logging(level=logging.INFO, formatter="json")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

register_exception_handlers(app)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    LoggingMiddleware,
    logger_name=__name__,
)

# TODO: implement vector_document repo, service and router
# app.include_router(vector_documents_router_v1, prefix="/api/v1")
app.include_router(ingest_overrides_router_v1, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/emit-test-event-get")
@app.post("/emit-test-event")
async def emit(request: Request):
    producer: KafkaProducer = request.app.state.kafka_producer

    msg = {"service": settings.APP_NAME, "message": "hello"}
    await producer.publish("test.topic", msg)

    return {"sent": True, "message": msg}


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="static/uploads"), name="uploads")


@app.get("/{path}")
async def catch_all(path: str | None = None):
    raise HTTPException(status_code=404, detail="Endpoint not found")
