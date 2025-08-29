import asyncio
import json
from typing import Any

from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import RunContext
from pydantic_ai.usage import Usage

from src.config.get_config import cfg
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition as Ai2ToolDefinition
from src.dao.engine_models.tool_definitions import ToolSource

from mcp import Tool as MCPTool


def build_fake_run_context():
    model = TestModel()
    usage = Usage()

    return RunContext(None, model, usage)


def get_mcp_tools():
    server = MCPServerStreamableHTTP(
        url=cfg.mcp.servers[0].url,
        headers=cfg.mcp.servers[0].headers,
    )
    tool_list: list[MCPTool] = asyncio.run(server.list_tools())

    return [
        Ai2ToolDefinition(
            name=tool.name,
            tool_source=ToolSource.MCP,
            description=tool.description or "",
            parameters=arg_parse_helper(tool.inputSchema) or {},
        )
        for tool in tool_list
    ]


def arg_parse_helper(args: str | dict[str, Any] | None) -> str | dict[str, Any] | None:
    if isinstance(args, str):
        try:
            return json.loads(args)
        except (json.JSONDecodeError, TypeError):
            pass

    return args


def call_mcp_tool(tool_call: ToolCall):
    server = MCPServerStreamableHTTP(
        url=cfg.mcp.servers[0].url,
        headers=cfg.mcp.servers[0].headers,
    )
    return str(asyncio.run(server.direct_call_tool(name=tool_call.tool_name, args=tool_call.args)))
