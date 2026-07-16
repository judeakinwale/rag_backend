import os
import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


os.environ.setdefault("PG_USER", "test")
os.environ.setdefault("PG_PASSWORD", "test")
os.environ.setdefault("PG_DB", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test"
)
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("INGEST_SERVICE_ORIGIN", "http://localhost:8000")
os.environ.setdefault("PGADMIN_DEFAULT_EMAIL", "test@example.com")
os.environ.setdefault("PGADMIN_DEFAULT_PASSWORD", "test")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("JWT_SECRET", "secret")
os.environ.setdefault("AZURE_TENANT_ID", "tenant")
os.environ.setdefault("AZURE_CLIENT_ID", "client")
os.environ.setdefault("AZURE_CLIENT_SECRET", "secret")
