from pydantic_ai import FunctionToolset

from src.custom_agents.dr_tulu.browse.browse_website_tool import browse_website
from src.custom_agents.dr_tulu.search.google_search_tool import google_search
from src.custom_agents.dr_tulu.search.snippet_search_tool import snippet_search

# TODO: See if a WrapperToolset could work better here https://ai.pydantic.dev/toolsets/#changing-tool-execution
dr_tulu_toolset = FunctionToolset(tools=[snippet_search, google_search, browse_website])
