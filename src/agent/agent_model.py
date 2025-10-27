from dataclasses import dataclass


@dataclass(kw_only=True)
class Agent:
    id: str
    name: str
    description: str
    short_summary: str
    information_url: str | None
    mcp_server_id: str | None
    model_id: str
    max_tokens: int
    temperature: float
    top_p: int
    stop: list[str]
    n: int
