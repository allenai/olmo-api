"""Environment settings with validation using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LITELLM_API_BASE: str = "https://ai2-model-hub.allen.ai"
    LITELLM_PROXY_API_KEY: str | None = None
    HF_TOKEN: str | None = None

    PGHOST: str | None = None
    PGPORT: str | None = None
    PGDATABASE: str | None = None
    PGUSER: str | None = None
    PGPASSWORD: str | None = None
    DB_SECRET_ARN: str | None = None

    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None


    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
