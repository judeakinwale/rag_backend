from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "User Service"

    PG_USER: str
    PG_PASSWORD: str
    PG_DB: str

    DATABASE_URL: str

    PGADMIN_DEFAULT_EMAIL: str
    PGADMIN_DEFAULT_PASSWORD: str

    KAFKA_BOOTSTRAP_SERVERS: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
