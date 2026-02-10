from typing import Any

from core import APIInterface
from core.tools.tool_source import ToolSource


class ToolCall(APIInterface):
    tool_name: str
    args: str | dict[str, Any] | None = None
    tool_call_id: str
    tool_source: ToolSource
