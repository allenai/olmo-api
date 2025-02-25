import datetime
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from logging import getLogger


class LogSeverity(StrEnum):
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


logSeverityToLevel = {
    LogSeverity.TRACE: 0,
    LogSeverity.DEBUG: 10,
    LogSeverity.INFO: 20,
    LogSeverity.WARNING: 30,
    LogSeverity.ERROR: 40,
    LogSeverity.FATAL: 50,
}


@dataclass
class LogEntry:
    severity: LogSeverity
    body: str
    resource: str
    timestamp: datetime.time = datetime.time()
    attributes: Mapping[str, str] | None = None
    type: str = "LogEntry"

    @property
    def is_valid(self) -> bool:
        return self.severity is not None or self.body is not None or self.resource is not None


def log(log_entry: LogEntry) -> None:
    logger = getLogger()

    level = logSeverityToLevel[log_entry.severity]

    logger.log(level=level, msg=json.dumps(log_entry.__dict__))
