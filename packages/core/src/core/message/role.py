from enum import StrEnum


class Role(StrEnum):
    User = "user"
    Assistant = "assistant"
    System = "system"
    ToolResponse = "tool_call_result"
