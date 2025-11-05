from pydantic_ai import RunContext, ToolReturn

from src.custom_agents.dr_tulu.dr_tulu_mcp_server import get_dr_tulu_mcp_server
from src.custom_agents.dr_tulu.search.format import format_search_output


async def snippet_search(
    query: str,
    ctx: RunContext,
    year: str | None = None,
    paper_ids: str | None = None,
    venue: str | None = None,
    limit: int = 10,
    fieldsOfStudy: str | None = None,  # noqa: N803
):
    mcp_server = get_dr_tulu_mcp_server()

    result = await mcp_server.direct_call_tool(
        "snippet_search",
        args={
            "query": query,
            "year": year,
            "paper_ids": paper_ids,
            "venue": venue,
            "limit": limit,
            "fieldsOfStudy": fieldsOfStudy,
        },
    )
    output = format_search_output(result, ctx)

    return ToolReturn(output, metadata={"raw_result": result})
