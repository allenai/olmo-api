from src.dao.engine_models.prompt_template import PromptTemplate
from src.dao.flask_sqlalchemy_session import current_session
from src.prompt_template.prompt_template_models import PromptTemplateResponseList


def get_prompt_templates_list() -> PromptTemplateResponseList:
    prompt_templates = current_session.query(PromptTemplate).where(PromptTemplate.deleted == None).all()  # noqa: E711

    return PromptTemplateResponseList.model_validate(prompt_templates)
