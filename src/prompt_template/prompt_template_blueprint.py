from datetime import datetime
from typing import Any

from flask import Blueprint
from pydantic import RootModel

from src.api_interface import APIInterface
from src.dao.engine_models.model_config import ModelType
from src.dao.engine_models.prompt_template import PromptTemplate
from src.dao.flask_sqlalchemy_session import current_session
from src.flask_pydantic_api.api_wrapper import pydantic_api


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


def get_prompt_templates() -> list[PromptTemplateResponse]:
    prompt_templates = current_session.query(PromptTemplate).where(PromptTemplate.deleted == None).all()  # noqa: E711
    return []


def create_prompt_template_blueprint() -> Blueprint:
    prompt_template_blueprint = Blueprint(name="prompt_template", import_name=__name__)

    @prompt_template_blueprint.get("/")
    @pydantic_api(
        name="Get available prompt templates",
        tags=["v4", "prompt templates"],
        model_dump_kwargs={"by_alias": True},
    )
    def get_prompt_templates() -> PromptTemplateResponseList:
        return PromptTemplateResponseList([])

    return prompt_template_blueprint
