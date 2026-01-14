# adapted from https://wazaari.dev/blog/fastapi-structlog-integration#context-variables
import re
from typing import Any

import structlog

from api.config import settings


class FastAPIStructLogger:
    def __init__(self, log_name: str = settings.LOG_NAME) -> None:
        self.logger = structlog.stdlib.get_logger(log_name)

    @staticmethod
    def _to_snake_case(name: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def bind(self, *args: Any, **new_values: Any):
        for arg in args:
            key = self._to_snake_case(type(arg).__name__)

            structlog.contextvars.bind_contextvars(**{key: arg.id})

        structlog.contextvars.bind_contextvars(**new_values)

    @staticmethod
    def unbind(*keys: str):
        structlog.contextvars.unbind_contextvars(*keys)

    def debug(self, event: str | None = None, *args: Any, **kw: Any):
        self.logger.debug(event, *args, **kw)

    def info(self, event: str | None = None, *args: Any, **kw: Any):
        self.logger.info(event, *args, **kw)

    def warning(self, event: str | None = None, *args: Any, **kw: Any):
        self.logger.warning(event, *args, **kw)

    warn = warning

    def error(self, event: str | None = None, *args: Any, **kw: Any):
        self.logger.error(event, *args, **kw)

    def critical(self, event: str | None = None, *args: Any, **kw: Any):
        self.logger.critical(event, *args, **kw)

    def exception(self, event: str | None = None, *args: Any, **kw: Any):
        self.logger.exception(event, *args, **kw)
