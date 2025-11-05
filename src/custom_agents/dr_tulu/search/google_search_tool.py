from pydantic_ai import RunContext, Tool, ToolReturn

from src.custom_agents.dr_tulu.dr_tulu_mcp_server import get_dr_tulu_mcp_server
from src.custom_agents.dr_tulu.search.format import format_search_output


async def google_search(
    ctx: RunContext,
    query: str,
    num: int = 10,
    gl: str = "us",
    hl: str = "en",
):
    mcp_server = get_dr_tulu_mcp_server()

    result = await mcp_server.direct_call_tool(
        "google_search",
        args={
            "query": query,
            "num": num,
            "gl": gl,
            "hl": hl,
        },
    )
    output = format_search_output(result, ctx)

    return ToolReturn(output, metadata={"raw_result": result})


google_search_tool = Tool(google_search)
