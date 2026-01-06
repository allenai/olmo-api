from datetime import datetime
from typing import Any

from pydantic import Field, RootModel

from db.models.model_config import ModelType
from src.api_interface import APIInterface
from src.thread.thread_models import InferenceOptionsResponse, ToolDefinition


class PromptTemplateResponse(APIInterface):
    id: str
    name: str
    content: str
    creator: str
    created: datetime
    updated: datetime

    opts: InferenceOptionsResponse
    model_type: ModelType
    file_urls: list[str] | None
    tool_definitions: list[ToolDefinition]

    extra_parameters: dict[str, Any] | None = Field(default=None)


class PromptTemplateResponseList(RootModel):
    root: list[PromptTemplateResponse]
