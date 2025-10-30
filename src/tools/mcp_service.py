import asyncio
from functools import lru_cache
from logging import getLogger

from pydantic_ai.mcp import MCPServer as PydanticMCPServer
from pydantic_ai.mcp import MCPServerStreamableHTTP

from src.config.Config import McpServer
from src.config.get_config import cfg, get_config
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from src.dao.engine_models.tool_definitions import ToolSource


@lru_cache
def get_mcp_servers() -> dict[str, MCPServerStreamableHTTP]:
    return {
        server.id: MCPServerStreamableHTTP(server.url, headers=server.headers, tool_prefix=server.id)
        for server in get_config().mcp.servers
    }


def get_tools_from_mcp_server(server: PydanticMCPServer) -> list[Ai2ToolDefinition]:
    # HACK: get_tools wants the context but doesn't actually use it yet
    tools = asyncio.run(server.get_tools(None))  # type: ignore

    return [
        Ai2ToolDefinition(
            name=tool.tool_def.name,
            tool_source=ToolSource.MCP,
            mcp_server_id=server.id,
            description=tool.tool_def.description or "",
            parameters=tool.tool_def.parameters_json_schema,
        )
        for tool in tools.values()
    ]


def get_mcp_tools() -> list[Ai2ToolDefinition]:
    return [tool for server in get_mcp_servers().values() for tool in get_tools_from_mcp_server(server)]


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
