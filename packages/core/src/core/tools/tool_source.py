from enum import StrEnum


class ToolSource(StrEnum):
    # where did this tool come from
    INTERNAL = "internal"
    USER_DEFINED = "user_defined"
    MCP = "model_context_protocol"
