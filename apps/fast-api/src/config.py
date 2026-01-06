from enum import StrEnum

from fastapi_structlog import LogSettings
from fastapi_structlog.settings import DBSettings, SysLogSettings
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
    log: LogSettings
    # config: Config


log_settings = LogSettings(syslog=SysLogSettings(), db=DBSettings())

settings = Settings(log=log_settings)
