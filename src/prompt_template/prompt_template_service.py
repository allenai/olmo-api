from sqlalchemy.orm import Session

from src.prompt_template.prompt_template_models import PromptTemplateResponseList
from src.prompt_template.prompt_template_repository import get_prompt_templates


def get_prompt_templates_list(session: Session) -> PromptTemplateResponseList:
    prompt_templates = get_prompt_templates(session)

    return PromptTemplateResponseList.model_validate(prompt_templates)
