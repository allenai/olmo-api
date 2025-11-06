import json
import logging
from typing import Any

from pydantic_ai import Tool, ToolReturn
from src.custom_agents.dr_tulu.dr_tulu_toolset import DR_TULU_TOOLS
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from src.dao.engine_models.tool_definitions import ToolSource

from .internal_tools import CreateRandomNumber

PUBLIC_TOOLS: list[Tool[Any]] = [CreateRandomNumber]
TOOL_REGISTRY: list[Tool[Any]] = [*PUBLIC_TOOLS, *DR_TULU_TOOLS]


def get_public_internal_tools() -> list[Ai2ToolDefinition]:
    return [
        Ai2ToolDefinition(
            name=tool.name,
            tool_source=ToolSource.INTERNAL,
            description=tool.description or "",
            parameters=tool.tool_def.parameters_json_schema or {},
        )
        for tool in PUBLIC_TOOLS
    ]


def get_all_internal_tools() -> list[Ai2ToolDefinition]:
    return [
        Ai2ToolDefinition(
            name=tool.name,
            tool_source=ToolSource.INTERNAL,
            description=tool.description or "",
            parameters=tool.tool_def.parameters_json_schema or {},
        )
        for tool in TOOL_REGISTRY
    ]


def call_internal_tool(tool_call: ToolCall) -> str:
    found_tool = next((tool for tool in TOOL_REGISTRY if tool_call.tool_name == tool.name), None)

    if found_tool is None:
        return "Could not find tool"

    try:
        if found_tool.takes_ctx is True:
            return "Tool setup incorrect"

        parsed_args = arg_parse_helper(tool_call.args)

        if isinstance(parsed_args, dict):
            result = found_tool.function(**parsed_args)  # type: ignore
        elif parsed_args is None:
            result = found_tool.function()  # type: ignore
        else:
            result = found_tool.function(parsed_args)  # type: ignore

        if isinstance(result, ToolReturn):
            return str(result.return_value)

        return str(result)

    except Exception as e:
        logging.exception("Tool call failed")
        return str(e)  # This returns the error to LLM


def arg_parse_helper(args: str | dict[str, Any] | None) -> str | dict[str, Any] | None:
    if isinstance(args, str):
        try:
            return json.loads(args)
        except (json.JSONDecodeError, TypeError):
            pass

    return args
