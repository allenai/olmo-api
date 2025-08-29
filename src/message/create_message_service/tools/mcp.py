from pydantic_ai.mcp import MCPServerSSE
from pydantic_ai.tools import RunContext
from pydantic_ai.usage import Usage
from pydantic_ai.models.test import TestModel
from pydantic_ai.models import Model

from src.config.get_config import cfg


def get_mcp_tools(model: Model):
    server = MCPServerSSE(
        url=cfg.mcp.servers[0].url,
        headers=cfg.mcp.servers[0].headers,
    )
    usage = Usage()

    run_context = RunContext(None, model, usage)
    tools = server.get_tools(run_context)
    return tools


print("MCP tools loaded")
print(get_mcp_tools(TestModel()))
