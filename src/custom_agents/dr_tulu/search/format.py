from pydantic_ai import RunContext
from pydantic_ai.mcp import ToolResult

from src.custom_agents.dr_tulu.search.document import Document


def format_search_output(output: ToolResult, ctx: RunContext):
    data = output.get("data", [])
    documents = []

    for item in data:
        if isinstance(item, dict):
            # Handle structured response with snippet and paper info
            if "snippet" in item and "paper" in item:
                snippet_info = item.get("snippet", {})
                paper_info = item.get("paper", {})

                if snippet_info.get("snippetKind") == "title":
                    snippet_text = ""
                else:
                    snippet_text = snippet_info.get("text", "").strip()

                doc = Document(
                    title=paper_info.get("title", "").strip(),
                    snippet=snippet_text,
                    url="",  # Semantic Scholar doesn't provide direct URLs in snippet search
                    text="",  # No full text content from search
                    score=item.get("score"),
                )

                if doc.title or doc.snippet:
                    documents.append(doc)

            # Handle direct snippet text (fallback case)
            elif "snippet" in item:
                snippet_text = item["snippet"].get("text", "").strip()
                if snippet_text:
                    doc = Document(title="", snippet=snippet_text, url="", text="", score=None)
                    documents.append(doc)

    combined_snippet_text = []
    for index, doc in enumerate(documents):
        combined_snippet_text.append(f"<snippet id={ctx.tool_call_id}-{index}>\n{doc.stringify()}\n</snippet>")
    return "\n".join(combined_snippet_text)
