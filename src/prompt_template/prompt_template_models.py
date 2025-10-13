from datetime import datetime
from typing import Any

from pydantic import RootModel

from src.api_interface import APIInterface
from src.dao.engine_models.model_config import ModelType
from src.thread.thread_models import ToolDefinition


class PromptTemplateResponse(APIInterface):
    id: str
    name: str
    content: str
    creator: str
    created: datetime
    updated: datetime

    opts: dict[str, Any]
    model_type: ModelType
    file_urls: list[str] | None
    tool_definitions: list[ToolDefinition]


class PromptTemplateResponseList(RootModel):
    root: list[PromptTemplateResponse]
