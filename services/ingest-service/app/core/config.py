from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# project's base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "Ingest Service"

    PG_USER: str
    PG_PASSWORD: str
    PG_DB: str

    DATABASE_URL: str

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

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",  # ".env"
        extra="ignore",
    )

    # class Config:
    #     env_file = BASE_DIR / ".env"  # ".env"
    #     extra = "ignore"


settings = Settings()
