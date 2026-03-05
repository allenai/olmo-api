from enum import StrEnum


class ErrorCode(StrEnum):
    TOOL_CALL_ERROR = "toolCallError"
    OTHER_ERROR = "otherError"


class ErrorSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
