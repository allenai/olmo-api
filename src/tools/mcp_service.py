import asyncio
from functools import lru_cache
from logging import getLogger

from attr import dataclass
from pydantic_ai.mcp import MCPServer as PydanticMCPServer
from pydantic_ai.mcp import MCPServerStreamableHTTP

from src.config.get_config import get_config
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from src.dao.engine_models.tool_definitions import ToolSource


@dataclass
class MCPServerWithConfig:
    id: str
    server: MCPServerStreamableHTTP
    enabled: bool
    available_for_all_models: bool


@lru_cache
def get_mcp_servers() -> dict[str, MCPServerWithConfig]:
    return {
        server.id: MCPServerWithConfig(
            id=server.id,
            server=MCPServerStreamableHTTP(
                id=server.id,
                url=server.url,
                headers=server.headers,
                tool_prefix=server.id if server.skip_tool_name_prefix is False else None,
            ),
            enabled=server.enabled,
            available_for_all_models=server.available_for_all_models,
        )
        for server in get_config().mcp.servers
    }


def get_tools_from_mcp_server(server: PydanticMCPServer) -> list[Ai2ToolDefinition]:
    # HACK: get_tools wants the context but doesn't actually use it yet
    tools = asyncio.run(server.get_tools(None))  # type:ignore

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


def _is_mcp_server_for_general_use(mcp_server: MCPServerWithConfig) -> bool:
    return mcp_server.enabled and mcp_server.available_for_all_models


def get_general_mcp_tools() -> list[Ai2ToolDefinition]:
    mcp_tools: list[Ai2ToolDefinition] = []

    mcp_servers = get_mcp_servers()

    # TODO: There's probably a way to share this logic with get_tools_from_mcp_servers
    # It may be nice to pass in a condition for the mcp servers?
    mcp_tools = [
        tool
        for server_id, server_config in mcp_servers.items()
        if _is_mcp_server_for_general_use(server_config)
        for tool in get_tools_from_mcp_server(server_config.server)
    ]

    return mcp_tools


def get_tools_from_mcp_servers(mcp_server_ids: set[str]) -> list[Ai2ToolDefinition]:
    mcp_servers = get_mcp_servers()

    mcp_tools = [
        tool
        for server_id, server_config in mcp_servers.items()
        if server_id in mcp_server_ids
        for tool in get_tools_from_mcp_server(server_config.server)
    ]

    return mcp_tools


def find_mcp_config_by_id(mcp_id: str | None) -> MCPServerWithConfig | None:
    if mcp_id is None:
        return None

    mcp_servers = get_mcp_servers()
    return mcp_servers.get(mcp_id, None)


def call_mcp_tool(tool_call: ToolCall, tool_definition: Ai2ToolDefinition):
    mcp_config = find_mcp_config_by_id(tool_definition.mcp_server_id)

    if mcp_config is None:
        msg = "Could not find mcp config."
        raise RuntimeError(msg)

    if mcp_config.enabled is False:
        msg = "the selected mcp server is not enabled"
        raise RuntimeError(msg)

    try:
        tool_name_without_prefix = tool_call.tool_name.removeprefix(f"{mcp_config.server.tool_prefix}_")
        tool_result = asyncio.run(
            mcp_config.server.direct_call_tool(name=tool_name_without_prefix, args=tool_call.args or {})
        )
        return str(tool_result)
    except Exception as _e:
        getLogger().exception("Failed to call mcp tool.", extra={"tool_name": tool_call.tool_name})
        return f"Failed to call remote tool {tool_call.tool_name}"
