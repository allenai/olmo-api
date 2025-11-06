from dataclasses import dataclass
from typing import Any

from pydantic_ai.toolsets import AbstractToolset


@dataclass(kw_only=True)
class Agent:
    id: str
    name: str
    description: str
    short_summary: str
    information_url: str | None
    mcp_server_ids: list[str] | None
    model_id: str
    max_tokens: int
    temperature: float
    top_p: int
    stop: list[str]
    n: int
    toolsets: list[AbstractToolset] | None = None
    extra_inference_opts: dict[str, Any] | None = None
