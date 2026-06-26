from app.events import ingest_events
from rag_packages.contracts.events.shared_events import DLQEvent


EVENTS = {
    "ingest.created": ingest_events.IngestCreatedEvent,
    "ingest.created.dlq": DLQEvent,
    "ingest.updated": ingest_events.IngestUpdatedEvent,
    "ingest.updated.dlq": DLQEvent,
    "ingest.softdeleted": ingest_events.IngestSoftDeletedEvent,
    "ingest.softdeleted.dlq": DLQEvent,
    "ingest.deleted": ingest_events.IngestDeletedEvent,
    "ingest.deleted.dlq": DLQEvent,
}
