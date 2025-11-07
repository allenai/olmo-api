import asyncio
from dataclasses import dataclass

from pydantic import BaseModel

from pydantic_ai import Tool, ToolReturn
from src.custom_agents.dr_tulu.dr_tulu_mcp_server import get_dr_tulu_mcp_server
from src.custom_agents.dr_tulu.search.document import Document
from src.custom_agents.dr_tulu.util import create_call_id


class Crawl4aiApiResult(BaseModel):
    """Result structure returned by Crawl4AI Docker API."""

    url: str
    success: bool
    markdown: str = ""
    fit_markdown: str | None = None
    html: str = ""
    error: str | None = None


@dataclass
class DocumentToolOutput:
    documents: list[Document]
    query: str | None = None


def _extract_raw_content_from_response(raw_output: Crawl4aiApiResult) -> str | None:
    """Extract raw text content from Crawl4AI response"""
    # Check if crawling was successful
    if not raw_output.success:
        return None

    return raw_output.fit_markdown or raw_output.markdown or raw_output.html


def _extract_metadata_from_document(raw_output: Crawl4aiApiResult) -> tuple[str | None, str | None]:
    """Extract metadata for display from Crawl4AI response"""
    # Check if crawling was successful
    if not raw_output.success:
        error_msg = raw_output.error or "Unknown error"
        fallback_message = f"Note: Crawl4AI failed ({error_msg}), using search snippet"
        return None, fallback_message

    # Crawl4AI doesn't provide webpage title
    webpage_title = None

    # Handle case where no content was extracted
    full_content = raw_output.fit_markdown or raw_output.markdown or raw_output.html

    if not full_content:
        fallback_message = "Note: No content extracted by Crawl4AI, using search snippet"
        return webpage_title, fallback_message

    return webpage_title, None


def browse_webpage(
    query: str,
) -> ToolReturn:
    mcp_server = get_dr_tulu_mcp_server()

    result = asyncio.run(
        mcp_server.direct_call_tool(
            "google_search",
            args={
                "url": query,
            },
        )
    )

    parsed_result = Crawl4aiApiResult.model_validate(result)

    webpage_title, fallback_message = _extract_metadata_from_document(parsed_result)

    document = Document(
        title="",
        snippet="",
        url=query,
        score=None,
        text=_extract_raw_content_from_response(parsed_result),
        error=parsed_result.error,
    )

    output = document.stringify(
        webpage_title=webpage_title, use_localized_snippets=True, context_chars=2000, fallback_message=fallback_message
    )

    call_id = create_call_id()

    return ToolReturn(
        return_value=f'<webpage id="{call_id}-0">\n{output}</webpage>',
        metadata={"should_truncate": True, "raw_result": parsed_result},
    )


browse_website_tool = Tool(browse_webpage, takes_ctx=False)
