import json
import logging
from typing import Any

from pydantic_ai import Tool
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.tools import ToolDefinition

from .internal_tools import CreateRandomNumber

logging.basicConfig()
logging.getLogger().setLevel(logging.NOTSET)

TOOL_REGISTRY: list[Tool[Any]] = [CreateRandomNumber]


def get_tools() -> list[ToolDefinition]:
    return [tool.tool_def for tool in TOOL_REGISTRY]


def call_tool_function(tool_call: ToolCallPart):
    found_tool = next((tool for tool in TOOL_REGISTRY if tool_call.tool_name == tool.name), None)

    if found_tool is None:
        return "Could not find tool"

    try:
        if found_tool.takes_ctx is False:
            parsed_args = arg_parse_helper(tool_call.args)
            if isinstance(parsed_args, dict):
                return found_tool.function(**parsed_args)  # type: ignore
            if parsed_args is None:
                return found_tool.function()  # type: ignore

            return found_tool.function(parsed_args)  # type: ignore
        return "Tool setup incorrect"

    except Exception:
        logging.exception("tool call failed")

        return "Failed to call tool"


def call_tool(tool_call: ToolCallPart) -> ToolReturnPart:
    tool_response = call_tool_function(tool_call)

    return ToolReturnPart(tool_name=tool_call.tool_name, content=tool_response, tool_call_id=tool_call.tool_call_id)


def arg_parse_helper(args: str | dict[str, Any] | None) -> str | dict[str, Any] | None:
    if isinstance(args, str):
        try:
            return json.loads(args)
        except (json.JSONDecodeError, TypeError):
            pass

    return args
