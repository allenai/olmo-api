"""Environment settings with validation using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LITELLM_API_BASE: str = "https://ai2-model-hub.allen.ai"
    LITELLM_PROXY_API_KEY: str | None = None
    HF_TOKEN: str | None = None
    GITHUB_TOKEN: str | None = None

    # Database configuration (defaults match olmo-eval)
    PGHOST: str = "localhost"
    PGPORT: str = "5432"
    PGDATABASE: str = "olmo_eval"
    PGUSER: str = "postgres"
    PGPASSWORD: str | None = None
    DB_SECRET_ARN: str | None = None

    # AWS credentials and settings
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"

    # Settings below are set at runtime and control evaluation behavior. They shouldn't
    # be set in .env files, but are included here for validation and documentation.

    # Runtime CLI parameters
    LOCAL: bool = False
    EVAL_MODE: str | None = None
    EVAL_TIER: str | None = None
    CLOUD_RUN_TASK_INDEX: int = 0

    # Ad-hoc runtime evaluation parameters
    AD_HOC_MODEL: str | None = None
    AD_HOC_TASKS: str | None = None
    AD_HOC_PROVIDER_KIND: str = "litellm"
    AD_HOC_HARNESS_OVERRIDES: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
