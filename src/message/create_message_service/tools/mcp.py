from pydantic_ai.mcp import MCPServerSSE
from pydantic_ai.tools import RunContext


def get_mcp_tools():
    server = MCPServerSSE(
        url="https://asta-tools.allen.ai/mcp/v1",
        headers={
            "x-api-key": "",
        },
    )

    run_context = RunContext()

    tools = server.get_tools(run_context)
    return tools
