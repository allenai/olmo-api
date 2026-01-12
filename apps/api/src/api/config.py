import os
from enum import StrEnum

from pydantic import Field
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


ENV = os.getenv("ENV", Environment.PRODUCTION.value)


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

    # Testing
    E2E_AUTH0_CLIENT_ID: str | None = None
    E2E_AUTH0_CLIENT_SECRET: str | None = None

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=(".env", f".env.{ENV}", ".env.local", f".env.{ENV}.local"),
        secrets_dir="/secret/env",
    )


settings = Settings()
