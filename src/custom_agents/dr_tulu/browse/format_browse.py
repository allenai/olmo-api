from pydantic_ai import RunContext
from pydantic_ai.mcp import ToolResult


def format_browse_output(output: ToolResult, ctx: RunContext):
    assert isinstance(output, dict)
