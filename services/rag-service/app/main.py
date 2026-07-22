import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.lifespan import lifespan
from app.core.config import settings
from app.api.v1.chats import router as chats_router_v1

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

origins = [
    "https://klafgo6.sharepoint.com",
    "https://localhost:3000",
    "http://localhost:3000",
    "https://localhost:5173",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    LoggingMiddleware,
    logger_name=__name__,
)

app.include_router(chats_router_v1, prefix="/api/v1")


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
