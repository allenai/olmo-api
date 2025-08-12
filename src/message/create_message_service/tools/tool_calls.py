import json
import logging
from typing import Any

from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.tools import ToolDefinition

from .internal_tools import Add, Subtract

logging.basicConfig()
logging.getLogger().setLevel(logging.NOTSET)


TOOL_REGISTRY = [Add, Subtract]


def get_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name=tool.__name__.lower(), description=tool.__doc__, parameters_json_schema=tool.model_json_schema()
        )
        for tool in TOOL_REGISTRY
    ]


def call_tool_function(tool_call: ToolCallPart):
    parsed_args = arg_parse_helper(tool_call.args)

    found_tool = next((tool for tool in TOOL_REGISTRY if tool_call.tool_name == tool.__name__.lower()), None)

    if found_tool is None:
        return "Could not find tool"
    try:
        return found_tool.call(parsed_args)
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
