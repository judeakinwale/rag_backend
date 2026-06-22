from fastapi import FastAPI
from app.kafka_producer import publish_event

app = FastAPI(title="ingest-service")

@app.get("/health")
def health():
    return {"status": "ok", "service": "ingest-service"}

@app.post("/emit-test-event")
def emit():
    publish_event("test.topic", {"service": "ingest-service", "message": "hello"})
    return {"sent": True}
