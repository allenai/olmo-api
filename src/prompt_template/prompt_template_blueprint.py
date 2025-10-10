from flask import Blueprint

from src.flask_pydantic_api.api_wrapper import pydantic_api
from src.prompt_template.prompt_template_models import PromptTemplateResponseList
from src.prompt_template.prompt_template_service import get_prompt_templates_list


def create_prompt_template_blueprint() -> Blueprint:
    prompt_template_blueprint = Blueprint(name="prompt_template", import_name=__name__)

    @prompt_template_blueprint.get("/")
    @pydantic_api(
        name="Get available prompt templates",
        tags=["v4", "prompt templates"],
        model_dump_kwargs={"by_alias": True},
    )
    def get_prompt_templates() -> PromptTemplateResponseList:
        return get_prompt_templates_list()

    return prompt_template_blueprint
