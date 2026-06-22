from fastapi import FastAPI
from app.kafka_producer import publish_event

app = FastAPI(title="rag-service")


@app.get("/")
def root():
    return {"message": "rag-service is running"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-service"}


@app.post("/emit-test-event")
def emit():
    publish_event("test.topic", {"service": "rag-service", "message": "hello"})
    return {"sent": True}
