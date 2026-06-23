from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# project's base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "User Service"

    PG_USER: str
    PG_PASSWORD: str
    PG_DB: str

    DATABASE_URL: str

    PGADMIN_DEFAULT_EMAIL: str
    PGADMIN_DEFAULT_PASSWORD: str

    KAFKA_BOOTSTRAP_SERVERS: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",  # ".env"
        extra="ignore",
    )

    # class Config:
    #     env_file = BASE_DIR / ".env"  # ".env"
    #     extra = "ignore"


settings = Settings()
