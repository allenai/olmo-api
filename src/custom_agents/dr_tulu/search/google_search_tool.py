import asyncio

from pydantic_ai import Tool, ToolReturn
from src.custom_agents.dr_tulu.dr_tulu_mcp_server import get_dr_tulu_mcp_server
from src.custom_agents.dr_tulu.search.format import format_search_output


def google_search(
    query: str,
    num: int = 10,
    gl: str = "us",
    hl: str = "en",
):
    mcp_server = get_dr_tulu_mcp_server()

    result = asyncio.run(
        mcp_server.direct_call_tool(
            "google_search",
            args={
                "query": query,
                "num": num,
                "gl": gl,
                "hl": hl,
            },
        )
    )
    output = format_search_output(result)

    return ToolReturn(output, metadata={"raw_result": result})


google_search_tool = Tool(google_search, takes_ctx=False)
