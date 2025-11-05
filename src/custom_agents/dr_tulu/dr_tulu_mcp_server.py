from functools import lru_cache

from pydantic_ai.mcp import MCPServerStreamableHTTP

from src.config.get_config import get_config


@lru_cache
def get_dr_tulu_mcp_server():
    config = get_config()

    dr_tulu_config = next(server for server in config.mcp.servers if server.id == "dr-tulu")
    return MCPServerStreamableHTTP(url=dr_tulu_config.url, headers=dr_tulu_config.headers)
