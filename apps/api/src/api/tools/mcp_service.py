import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from pydantic_ai.mcp import MCPServerStreamableHTTP

from api.config import settings
from api.logging.fastapi_logger import FastAPIStructLogger
from db.models.tool_call import ToolCall
from db.models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from db.models.tool_definitions import ToolSource

if TYPE_CHECKING:
    from mcp import Tool as MCPTool

logger = FastAPIStructLogger()


@dataclass
class McpServer:
    """MCP Server configuration for FastAPI app."""

    url: str
    headers: dict[str, str]
    name: str
    id: str
    enabled: bool
    available_for_all_models: bool = True


# MCP Server Configuration
# TODO: Move MCP Servers list to database in the future
MCP_SERVERS: list[McpServer] = [
    McpServer(
        name="Asta",
        id="asta",
        url="https://asta-tools.allen.ai/mcp/v1",
        headers={"x-api-key": settings.ASTA_MCP_API_KEY},
        enabled=True,
        available_for_all_models=True,
    ),
]


def _get_mcp_server(mcp_server_config: McpServer):
    return MCPServerStreamableHTTP(url=mcp_server_config.url, headers=mcp_server_config.headers)


@lru_cache
def _get_general_mcp_servers():
    return [_get_mcp_server(config) for config in MCP_SERVERS]


class McpService:
    def __init__(self) -> None:
        # Per-request cache for MCP server tools (keyed by server id)
        self._server_tools_cache: dict[str, list[Ai2ToolDefinition]] = {}

    @staticmethod
    async def list_mcp_server_tools(mcp_server_config: McpServer) -> list[Ai2ToolDefinition]:
        mcp_server = _get_mcp_server(mcp_server_config)

        tool_list: list[MCPTool] = await mcp_server.list_tools()
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

    @staticmethod
    def _is_mcp_server_for_general_use(mcp_server: McpServer) -> bool:
        return mcp_server.enabled and mcp_server.available_for_all_models

    @staticmethod
    def find_mcp_config_by_id(mcp_id: str | None) -> McpServer | None:
        if mcp_id is None:
            return None

        return next((config for config in MCP_SERVERS if config.id == mcp_id), None)

    async def _get_tools_for_servers(self, servers: list[McpServer]) -> list[Ai2ToolDefinition]:
        """Fetch tools from servers, using per-request cache to avoid duplicate calls."""
        uncached_servers = [s for s in servers if s.id not in self._server_tools_cache]

        # Fetch and cache tools for servers not in cache
        if uncached_servers:
            server_tool_lists = await asyncio.gather(
                *[self.list_mcp_server_tools(server) for server in uncached_servers],
                return_exceptions=True,
            )

            for server, tools in zip(uncached_servers, server_tool_lists, strict=True):
                if isinstance(tools, BaseException):
                    logger.warning("Failed to fetch tools from MCP server", tools=tools)
                    self._server_tools_cache[server.id] = []
                else:
                    self._server_tools_cache[server.id] = tools

        mcp_tools: list[Ai2ToolDefinition] = []
        for server in servers:
            mcp_tools.extend(self._server_tools_cache.get(server.id, []))

        return mcp_tools

    async def get_general_mcp_tools(self) -> list[Ai2ToolDefinition]:
        general_mcp_servers = [server for server in MCP_SERVERS if self._is_mcp_server_for_general_use(server)]

        if not general_mcp_servers:
            return []

        return await self._get_tools_for_servers(general_mcp_servers)

    async def get_tools_from_mcp_servers(self, mcp_server_ids: set[str]) -> list[Ai2ToolDefinition]:
        matching_servers = [server for server in MCP_SERVERS if server.id in mcp_server_ids]

        if not matching_servers:
            return []

        return await self._get_tools_for_servers(matching_servers)

    def call_mcp_tool(self, tool_call: ToolCall, tool_definition: Ai2ToolDefinition):
        mcp_config = self.find_mcp_config_by_id(tool_definition.mcp_server_id)

        if mcp_config is None:
            msg = "Could not find mcp config."
            raise RuntimeError(msg)

        if mcp_config.enabled is False:
            msg = "the selected mcp server is not enabled"
            raise RuntimeError(msg)

        try:
            server = _get_mcp_server(mcp_config)
            return str(asyncio.run(server.direct_call_tool(name=tool_call.tool_name, args=tool_call.args or {})))
        except Exception as _e:
            logger.exception("Failed to call mcp tool.", tool_name=tool_call.tool_name)
            return f"Failed to call remote tool {tool_call.tool_name}"

    @classmethod
    def get_pydantic_ai_mcp_servers(cls) -> list[MCPServerStreamableHTTP]:
        return _get_general_mcp_servers()


McpServiceDependency = Annotated[McpService, Depends()]
