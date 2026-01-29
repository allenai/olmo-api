from typing import Any

from core import APIInterface
from core.tools.tool_source import ToolSource


class ToolDefinition(APIInterface):
    name: str
    description: str
    parameters: dict[str, Any] | None = None
    tool_source: ToolSource
