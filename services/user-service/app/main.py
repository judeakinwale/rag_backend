import sys
import logging

from fastapi import FastAPI, Request

from app.api.v1.users import router as user_router
from app.lifespan import lifespan

from app.middleware.request_id import RequestIdMiddleware
from rag_packages.shared.logging.middleware import LoggingMiddleware
from rag_packages.shared.logging.packages import enable_package_logging
from rag_packages.shared.logging.config import setup_logging


setup_logging()
enable_package_logging(level=logging.INFO, formatter="json")

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# # StreamHandler for logging to console (stdout)
# stream_handler = logging.StreamHandler(sys.stdout)
# log_formatter = logging.Formatter(
#     "%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s"
# )
# stream_handler.setFormatter(log_formatter)
# logger.addHandler(stream_handler)


app = FastAPI(title="user-service", lifespan=lifespan)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    LoggingMiddleware,
    logger_name=__name__,
)

app.include_router(user_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "user-service"}


@app.post("/emit-test-event")
async def emit(request: Request):
    # await publish_event("test.topic", {"service": "user-service", "message": "hello"})

    msg = {"service": "user-service", "message": "hello"}
    await request.app.state.kafka_producer.publish(
        "test.topic", msg
    )
    print(f"Published message to test.topic: {msg}")
    
    return {"sent": True}


@app.get("/emit-test-event-get")
async def emit_get(request: Request):
    return await emit(request)
