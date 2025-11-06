from pydantic_ai.toolsets import FunctionToolset
from src.custom_agents.dr_tulu.browse.browse_website_tool import browse_website_tool
from src.custom_agents.dr_tulu.search.google_search_tool import google_search_tool
from src.custom_agents.dr_tulu.search.snippet_search_tool import snippet_search_tool

# TODO: See if we can use a WrapperToolset here https://ai.pydantic.dev/toolsets/#changing-tool-execution
DR_TULU_TOOLS = FunctionToolset(tools=[snippet_search_tool, google_search_tool, browse_website_tool])
