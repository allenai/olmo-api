from enum import StrEnum


class ErrorCode(StrEnum):
    TOOL_CALL_ERROR = "toolCallError"
    EXCEEDED_MAX_TOKENS = "exceededMaxTokens"
    MODEL_OVERLOADED = "modelOverloaded"

    UNKNOWN_ERROR = "unknownError"


class ErrorSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
