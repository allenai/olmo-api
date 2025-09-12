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


def get_mcp_tools():
    mcp_tools: list[Ai2ToolDefinition] = []
    for server in cfg.mcp.servers:
        if server.enabled is False:
            continue
        mcp_server = MCPServerStreamableHTTP(
            url=server.url,
            headers=server.headers,
        )
        tool_list: list[MCPTool] = asyncio.run(mcp_server.list_tools())
        mapped_tools = [
            Ai2ToolDefinition(
                name=tool.name,
                tool_source=ToolSource.MCP,
                mcp_server_id=server.id,
                description=tool.description or "",
                parameters=tool.inputSchema,
            )
            for tool in tool_list
        ]
        mcp_tools.extend(mapped_tools)

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
