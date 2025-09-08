from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.tools import ToolDefinition

from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from src.dao.engine_models.tool_definitions import ToolSource

from .internal_tools_service import call_internal_tool, get_internal_tools
from .mcp_service import call_mcp_tool, get_mcp_tools


def map_tool_def_to_pydantic(tool: Ai2ToolDefinition):
    return ToolDefinition(
        name=tool.name,
        description=tool.description,
        parameters_json_schema=tool.parameters or {},
    )


def get_pydantic_tool_defs(message: Message) -> list[ToolDefinition]:
    return (
        [map_tool_def_to_pydantic(tool_def) for tool_def in message.tool_definitions]
        if message.tool_definitions is not None
        else []
    )


def get_available_tools(model: ModelConfig):
    if model.can_call_tools is False:
        return []

    internal_tools = get_internal_tools()
    mcp_tools = get_mcp_tools()

    return internal_tools + mcp_tools


def call_tool(tool_call: ToolCall, tool_definition: Ai2ToolDefinition) -> ToolReturnPart:
    tool_response: str
    match tool_call.tool_source:
        case ToolSource.INTERNAL:
            tool_response = call_internal_tool(tool_call)
        case ToolSource.MCP:
            tool_response = call_mcp_tool(tool_call, tool_definition)
        case _:
            msg = f"Invalid tool source: {tool_call.tool_source}"
            raise ValueError(msg)

    return ToolReturnPart(
        tool_name=tool_call.tool_name,
        content=tool_response,
        tool_call_id=tool_call.tool_call_id,
    )
