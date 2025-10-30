import asyncio
from functools import lru_cache
from logging import getLogger

from pydantic_ai.mcp import MCPServer as PydanticMCPServer
from pydantic_ai.mcp import MCPServerStreamableHTTP

from src.config.get_config import get_config
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from src.dao.engine_models.tool_definitions import ToolSource


@lru_cache
def get_mcp_servers() -> dict[str, MCPServerStreamableHTTP]:
    return {
        server.id: MCPServerStreamableHTTP(server.url, headers=server.headers, tool_prefix=server.id)
        for server in get_config().mcp.servers
        if server.enabled
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


def find_mcp_config_by_id(mcp_server_id: str | None) -> MCPServerStreamableHTTP | None:
    if mcp_server_id is None:
        return None

    mcp_servers = get_mcp_servers()
    return mcp_servers.get(mcp_server_id, None)


def call_mcp_tool(tool_call: ToolCall, tool_definition: Ai2ToolDefinition):
    server = find_mcp_config_by_id(tool_definition.mcp_server_id)

    if server is None:
        msg = "Could not find mcp config."
        raise RuntimeError(msg)

    try:
        tool_name_without_prefix = tool_call.tool_name.removeprefix(f"{server.tool_prefix}_")
        tool_result = asyncio.run(server.direct_call_tool(name=tool_name_without_prefix, args=tool_call.args or {}))
        return str(tool_result)
    except Exception:
        getLogger().exception("Failed to call mcp tool.", extra={"tool_name": tool_call.tool_name})
        return f"Failed to call remote tool {tool_call.tool_name}"
