from enum import StrEnum

from pydantic_settings import BaseSettings


# Taken from https://github.com/zhanymkanov/fastapi_production_template/blob/main/src/constants.py#L12
class Environment(StrEnum):
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TEST = "TEST"

    @property
    def is_debug(self):
        return self == self.DEVELOPMENT

    @property
    def is_test(self):
        return self == self.TEST

    @property
    def is_production(self):
        return self == self.PRODUCTION


class Settings(BaseSettings):
    ENV: Environment = Environment.PRODUCTION
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = True
    LOG_NAME: str = "olmo-api.app_logs"
    LOG_ACCESS_NAME: str = "olmo-api.access_logs"


settings = Settings()
