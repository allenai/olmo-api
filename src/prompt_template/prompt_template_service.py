from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from src.dependencies import DBSession
from src.prompt_template.prompt_template_models import PromptTemplateResponseList
from src.prompt_template.prompt_template_repository import get_prompt_templates


def get_prompt_templates_list(session: Session) -> PromptTemplateResponseList:
    prompt_templates = get_prompt_templates(session)

    return PromptTemplateResponseList.model_validate(prompt_templates)


# Service class with dependency injection
class PromptTemplateService:
    """
    Prompt template service with dependency-injected database session.

    This service encapsulates prompt template operations and receives
    its dependencies through constructor injection.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_prompt_templates_list(self) -> PromptTemplateResponseList:
        """Get list of available prompt templates"""
        prompt_templates = get_prompt_templates(self.session)
        return PromptTemplateResponseList.model_validate(prompt_templates)


def get_prompt_template_service(session: DBSession) -> PromptTemplateService:
    """Dependency provider for PromptTemplateService"""
    return PromptTemplateService(session)


# Type alias for dependency injection
PromptTemplateServiceDep = Annotated[PromptTemplateService, Depends(get_prompt_template_service)]
