from dataclasses import dataclass
from typing import Any

from pydantic_ai.ui import UIAdapter

# UIAdapter[RequestData, UIMessage, BaseChunk, AgentDepsT, OutputDataT]
@dataclass
class PlaygroundUIAdapter(UIAdapter[Any, Any, Any, Any, Any])