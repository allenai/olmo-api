from typing import TYPE_CHECKING, Annotated

from fastapi.params import Depends
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.tools import ToolDefinition

from db.models.message import Message
from db.models.tool_call import ToolCall
from db.models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from db.models.tool_definitions import ToolSource

from .internal_tools_service import InternalToolServiceDependency
from .mcp_service import McpServiceDependency

if TYPE_CHECKING:
    from api.model.model_response import BaseModelResponse
    from db.models.model_config import ModelConfig


class ToolsService:
    def __init__(self, mcp_service: McpServiceDependency, internal_tool_service: InternalToolServiceDependency):
        self.mcp_service = mcp_service
        self.internal_tool_service = internal_tool_service

    @staticmethod
    def map_tool_def_to_pydantic(*, tool: Ai2ToolDefinition) -> ToolDefinition:
        tool_definition = ToolDefinition(
            name=tool.name,
            description=tool.description,
        )

        if tool.parameters is not None:
            # Pydantic-AI applies its own empty default if we don't provide anything. This lets us use that default without recreating it
            tool_definition.parameters_json_schema = tool.parameters

        return tool_definition

    def get_pydantic_tool_defs(self, *, message: Message) -> list[ToolDefinition]:
        return (
            [self.map_tool_def_to_pydantic(tool=tool_def) for tool_def in message.tool_definitions]
            if message.tool_definitions is not None
            else []
        )

    async def get_available_tools(self, *, model: ModelConfig | BaseModelResponse) -> list[Ai2ToolDefinition]:
        if model.can_call_tools is False:
            return []

        internal_tools = self.internal_tool_service.get_internal_tools()
        mcp_tools = await self.mcp_service.get_general_mcp_tools()

        return internal_tools + mcp_tools

    def call_tool(self, *, tool_call: ToolCall, tool_definition: Ai2ToolDefinition) -> ToolReturnPart:
        tool_response: str
        match tool_call.tool_source:
            case ToolSource.INTERNAL:
                tool_response = self.internal_tool_service.call_internal_tool(tool_call)
            case ToolSource.MCP:
                tool_response = self.mcp_service.call_mcp_tool(tool_call, tool_definition)
            case _:
                msg = f"Invalid tool source: {tool_call.tool_source}"
                raise ValueError(msg)

        return ToolReturnPart(
            tool_name=tool_call.tool_name,
            content=tool_response,
            tool_call_id=tool_call.tool_call_id,
        )


ToolsServiceDependency = Annotated[ToolsService, Depends()]
