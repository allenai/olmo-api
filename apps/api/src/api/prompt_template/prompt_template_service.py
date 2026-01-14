from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends
from pydantic import Field, RootModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.db.sqlalchemy_engine import SessionDependency
from core.api_interface import APIInterface
from db.models.inference_opts import InferenceOpts
from db.models.model_config import ModelType
from db.models.prompt_template import PromptTemplate
from db.models.tool_definitions import ToolSource


class InferenceOptionsResponse(InferenceOpts, APIInterface): ...

class ToolDefinition(APIInterface):
    name: str
    description: str
    parameters: dict[str, Any] | None = None
    tool_source: ToolSource

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

class PromptTemplateService:
    def __init__(self, session: SessionDependency):
        self.session = session

    async def get_all(self) -> PromptTemplateResponseList:
         async with self.session.begin():

            stmt = (select(PromptTemplate)
                    .where(PromptTemplate.deleted == None)  # noqa: E711
                    .options(selectinload(PromptTemplate.tool_definitions)))

            result = await self.session.scalars(stmt)

            processed_results = [PromptTemplateResponse.model_validate(model) for model in result.all()]

            return PromptTemplateResponseList.model_validate(processed_results)


PromptTemplateServiceDependency = Annotated[PromptTemplateService, Depends()]
