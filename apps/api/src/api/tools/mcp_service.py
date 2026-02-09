import asyncio
from dataclasses import dataclass
from logging import getLogger
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from pydantic_ai.mcp import MCPServerStreamableHTTP

from api.config import settings
from db.models.tool_call import ToolCall
from db.models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from db.models.tool_definitions import ToolSource

if TYPE_CHECKING:
    from mcp import Tool as MCPTool


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


class McpService:
    @staticmethod
    async def list_mcp_server_tools(mcp_server_config: McpServer) -> list[Ai2ToolDefinition]:
        mcp_server = MCPServerStreamableHTTP(
            url=mcp_server_config.url,
            headers=mcp_server_config.headers,
        )

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


    async def get_general_mcp_tools(self) -> list[Ai2ToolDefinition]:
        # TODO: There's probably a way to share this logic with get_tools_from_mcp_servers
        # It may be nice to pass in a condition for the mcp servers?
        general_mcp_servers = [server for server in MCP_SERVERS if self._is_mcp_server_for_general_use(server)]

        if not general_mcp_servers:
            return []

        server_tool_lists = await asyncio.gather(
            *[self.list_mcp_server_tools(server) for server in general_mcp_servers], return_exceptions=True
        )

        mcp_tools: list[Ai2ToolDefinition] = []
        for tools in server_tool_lists:
            if isinstance(tools, BaseException):
                getLogger().warning("Failed to fetch tools from MCP server", exc_info=tools)
            else:
                mcp_tools.extend(tools)

        return mcp_tools


    async def get_tools_from_mcp_servers(self, mcp_server_ids: set[str]) -> list[Ai2ToolDefinition]:
        matching_servers = [server for server in MCP_SERVERS if server.id in mcp_server_ids]

        if not matching_servers:
            return []

        server_tool_lists = await asyncio.gather(
            *[self.list_mcp_server_tools(server) for server in matching_servers], return_exceptions=True
        )

        mcp_tools: list[Ai2ToolDefinition] = []
        for tools in server_tool_lists:
            if isinstance(tools, BaseException):
                getLogger().warning("Failed to fetch tools from MCP server", exc_info=tools)
            else:
                mcp_tools.extend(tools)

        return mcp_tools


    def call_mcp_tool(self, tool_call: ToolCall, tool_definition: Ai2ToolDefinition):
        mcp_config = self.find_mcp_config_by_id(tool_definition.mcp_server_id)

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

McpServerDependency = Annotated[McpService, Depends()]
