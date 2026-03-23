import json
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends

from api.logging.fastapi_logger import FastAPIStructLogger
from db.models.tool_call import ToolCall
from db.models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from db.models.tool_definitions import ToolSource

if TYPE_CHECKING:
    from pydantic_ai import Tool

logger = FastAPIStructLogger()

TOOL_REGISTRY: list[Tool[Any]] = []


class InternalToolService:
    @staticmethod
    def get_internal_tools():
        return [
            Ai2ToolDefinition(
                name=tool.name,
                tool_source=ToolSource.INTERNAL,
                description=tool.description or "",
                parameters=tool.tool_def.parameters_json_schema or {},
            )
            for tool in TOOL_REGISTRY
        ]

    @staticmethod
    def arg_parse_helper(args: str | dict[str, Any] | None) -> str | dict[str, Any] | None:
        if isinstance(args, str):
            try:
                return json.loads(args)
            except json.JSONDecodeError, TypeError:
                pass

        return args

    def call_internal_tool(self, tool_call: ToolCall) -> str:
        found_tool = next((tool for tool in TOOL_REGISTRY if tool_call.tool_name == tool.name), None)

        if found_tool is None:
            return "Could not find tool"

        try:
            if found_tool.takes_ctx is False:
                parsed_args = self.arg_parse_helper(tool_call.args)
                if isinstance(parsed_args, dict):
                    return str(found_tool.function(**parsed_args))  # type: ignore
                if parsed_args is None:
                    return str(found_tool.function())  # type: ignore

                return str(found_tool.function(parsed_args))  # type: ignore
            return "Tool setup incorrect"

        except Exception as e:
            logger.exception("Tool call failed", tool_name=tool_call.tool_name)
            return str(e)  # This returns the error to LLM


InternalToolServiceDependency = Annotated[InternalToolService, Depends()]
