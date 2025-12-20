import asyncio
from logging import getLogger
from typing import TYPE_CHECKING

from pydantic_ai.mcp import MCPServerStreamableHTTP

from src.config.Config import McpServer
from src.config.get_config import cfg
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from src.dao.engine_models.tool_definitions import ToolSource

if TYPE_CHECKING:
    from mcp import Tool as MCPTool


def list_mcp_server_tools(mcp_server_config: McpServer) -> list[Ai2ToolDefinition]:
    mcp_server = MCPServerStreamableHTTP(
        url=mcp_server_config.url,
        headers=mcp_server_config.headers,
    )

    tool_list: list[MCPTool] = asyncio.run(mcp_server.list_tools())
    mapped_tools = [
        Ai2ToolDefinition(
            name=tool.name,
            tool_source=ToolSource.MCP,
            mcp_server_id=mcp_server_config.id,
            description=tool.description or "",
            parameters=tool.inputSchema,
        )
        for tool in tool_list
    ]

    return mapped_tools


def _is_mcp_server_for_general_use(mcp_server: McpServer) -> bool:
    return mcp_server.enabled and mcp_server.available_for_all_models


def get_general_mcp_tools() -> list[Ai2ToolDefinition]:
    mcp_tools: list[Ai2ToolDefinition] = []

    # TODO: There's probably a way to share this logic with get_tools_from_mcp_servers
    # It may be nice to pass in a condition for the mcp servers?
    mcp_tools = [
        tool
        for server in cfg.mcp.servers
        if _is_mcp_server_for_general_use(server)
        for tool in list_mcp_server_tools(server)
    ]

    return mcp_tools


def get_tools_from_mcp_servers(mcp_server_ids: set[str]) -> list[Ai2ToolDefinition]:
    mcp_tools = [
        tool for server in cfg.mcp.servers if server.id in mcp_server_ids for tool in list_mcp_server_tools(server)
    ]

    return mcp_tools


def find_mcp_config_by_id(mcp_id: str | None) -> McpServer | None:
    if mcp_id is None:
        return None

    return next((config for config in cfg.mcp.servers if config.id == mcp_id), None)


def call_mcp_tool(tool_call: ToolCall, tool_definition: Ai2ToolDefinition):
    mcp_config = find_mcp_config_by_id(tool_definition.mcp_server_id)

    if mcp_config is None:
        msg = "Could not find mcp config."
        raise RuntimeError(msg)

    if mcp_config.enabled is False:
        msg = "the selected mcp server is not enabled"
        raise RuntimeError(msg)

    try:
        server = MCPServerStreamableHTTP(
            url=mcp_config.url,
            headers=mcp_config.headers,
        )
        return str(asyncio.run(server.direct_call_tool(name=tool_call.tool_name, args=tool_call.args or {})))
    except Exception as _e:
        getLogger().exception("Failed to call mcp tool.", extra={"tool_name": tool_call.tool_name})
        return f"Failed to call remote tool {tool_call.tool_name}"
