from enum import StrEnum


class ErrorCode(StrEnum):
    TOOL_CALL_ERROR = "toolCallError"
    OTHER_ERROR = "otherError"
    FINALIZE_ERROR = "finalizeError"


class ErrorSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
