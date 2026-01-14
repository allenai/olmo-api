from fastapi import APIRouter

from api.prompt_template.prompt_template_service import PromptTemplateResponseList, PromptTemplateServiceDependency

prompt_template_router = APIRouter(prefix="/prompt-templates")

@prompt_template_router.get("/")
async def get_prompt_templates(
        prompt_template_service: PromptTemplateServiceDependency,
) -> PromptTemplateResponseList:
        return await prompt_template_service.get_all()
