from fastapi import FastAPI
from app.kafka_producer import publish_event

app = FastAPI(title="document-processor-service")

@app.get("/health")
def health():
    return {"status": "ok", "service": "document-processor-service"}

@app.post("/emit-test-event")
def emit():
    publish_event("test.topic", {"service": "document-processor-service", "message": "hello"})
    return {"sent": True}
