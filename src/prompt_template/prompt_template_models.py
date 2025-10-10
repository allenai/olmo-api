from datetime import datetime
from typing import Any

from pydantic import RootModel

from src.api_interface import APIInterface
from src.dao.engine_models.model_config import ModelType


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
    tool_definitions: Any  # TODO: Map Tool Definitions to a Pydantic model


class PromptTemplateResponseList(RootModel):
    root: list[PromptTemplateResponse]
