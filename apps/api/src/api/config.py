import os
from enum import StrEnum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Taken from https://github.com/zhanymkanov/fastapi_production_template/blob/main/src/constants.py#L12
class Environment(StrEnum):
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TEST = "test"

    @property
    def is_debug(self):
        return self == self.DEVELOPMENT

    @property
    def is_test(self):
        return self == self.TEST

    @property
    def is_production(self):
        return self == self.PRODUCTION


environment = os.getenv("ENV", Environment.PRODUCTION.value)


class Settings(BaseSettings):
    ENV: Environment = Environment.PRODUCTION

    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = True

    LOG_NAME: str = "olmo-api.app_logs"
    LOG_ACCESS_NAME: str = "olmo-api.access_logs"

    DATABASE_URL: str = Field(init=False)
    DATABASE_MIN_POOL_SIZE: int = 3
    DATABASE_MAX_OVERFLOW_CONNECTIONS: int = 5

    AUTH_DOMAIN: str = Field(init=False)
    AUTH_AUDIENCE: str = Field(init=False)

    HUBSPOT_URL: str = "https://api.hubapi.com"
    HUBSPOT_TOKEN: str = Field(init=False)
    ASTA_MCP_API_KEY: str = Field(init=False)

    OTEL_COLLECTOR_TYPE: str = "cloud"
    OTEL_SERVICE_NAME: str = "olmo-api"
    OTEL_GCP_PROJECT_ID: str = "ai2-reviz"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"

    INFINI_GRAM_API_URL: str = Field(init=False)

    AI2_MODEL_HUB_BASE_URL: str = "https://ai2-model-hub.allen.ai"
    AI2_MODEL_HUB_API_KEY: SecretStr = Field(init=False)

    BEAKER_ADDRESS: str = "beaker.org:443"
    BEAKER_USER_TOKEN: SecretStr = Field(init=False)

    CIRRASCALE_BASE_URL: str = "https://ai2endpoints.cirrascale.ai/api"
    CIRRASCALE_API_KEY: SecretStr = Field(init=False)

    MODAL_OPENAI_API_KEY: SecretStr = Field(init=False)

    USER_CONTENT_BUCKET: str = "ai2-playground-molmo"

    RECAPTCHA_ENABLED: bool = True
    RECAPTCHA_GCP_PROJECT_ID: str = "ai2-reviz"
    RECAPTCHA_KEY: str = Field(init=False)
    RECAPTCHA_MIN_SCORE_REQUIREMENT: float = 0.3

    SAFETY_QUEUE_ENABLED: bool = True
    SAFETY_QUEUE_URL: str = Field(init=False)
    SAFTEY_GCS_UPLOAD_BUCKET: str = Field(init=False)

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=(".env", f".env.{environment}", ".env.local", f".env.{environment}.local"),
        secrets_dir="/secret/env",
    )


settings = Settings()
