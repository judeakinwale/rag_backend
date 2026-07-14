from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# project's base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "Document Processor Service"

    PG_USER: str
    PG_PASSWORD: str
    PG_DB: str

    DATABASE_URL: str

    INGEST_SERVICE_ORIGIN: str

    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB in bytes
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    QDRANT_HOSTNAME: str
    QDRANT_PORT: str
    QDRANT_GRPC_PORT: str

    PGADMIN_DEFAULT_EMAIL: str
    PGADMIN_DEFAULT_PASSWORD: str

    KAFKA_BOOTSTRAP_SERVERS: str

    JWT_SECRET: str
    JWT_ALGORITHM: str | None = "HS256"
    JWT_TOKEN_URL: str | None = "/api/v1/auth/token"
    JWT_TOKEN_EXPIRES_IN: int | None = 3600 * 24  # in seconds, default is one day

    REDIS_HOST: str | None = "localhost"
    REDIS_PORT: int | None = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_CACHE_KEY_PREFIX: str | None = "ingest_service"

    SHAREPOINT_INGEST_POLL_ENABLED: bool = True
    SHAREPOINT_INGEST_POLL_INTERVAL_SECONDS: int = 300
    SHAREPOINT_INGEST_LOCK_TTL_SECONDS: int = 600

    SHAREPOINT_SITE_URL: str | None = "https://klafgo6.sharepoint.com/"
    SHAREPOINT_LIBRARY_IDS: list[str] | None = None

    # Entra Id Sharepoint Configuration
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",  # ".env"
        extra="ignore",
    )


settings = Settings()
