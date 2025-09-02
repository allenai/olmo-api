import asyncio
import json
from logging import getLogger
from typing import Any

from mcp import Tool as MCPTool
from pydantic_ai.mcp import MCPServerStreamableHTTP

from src.config.get_config import cfg
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from src.dao.engine_models.tool_definitions import ToolSource


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


def arg_parse_helper(args: str | dict[str, Any] | None) -> str | dict[str, Any] | None:
    if isinstance(args, str):
        try:
            return json.loads(args)
        except (json.JSONDecodeError, TypeError):
            pass

    return args


def call_mcp_tool(tool_call: ToolCall):
    try:
        server = MCPServerStreamableHTTP(
            url=cfg.mcp.servers[0].url,
            headers=cfg.mcp.servers[0].headers,
        )
        return str(asyncio.run(server.direct_call_tool(name=tool_call.tool_name, args=tool_call.args or {})))
    except Exception as _e:
        getLogger().exception("Failed to call mcp tool.", extra={"tool_name": tool_call.tool_name})
        return f"Failed to call remote tool {tool_call.tool_name}"
