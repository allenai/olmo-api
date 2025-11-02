"""
Prompt Template Router (FastAPI) - V4
--------------------------------------

FastAPI router for prompt template operations.
Converted from Flask blueprint in prompt_template_blueprint.py.
"""

import asyncio

from fastapi import APIRouter

from src.prompt_template.prompt_template_models import PromptTemplateResponseList
from src.prompt_template.prompt_template_service import (
    PromptTemplateServiceDep,
    get_prompt_templates_list,
)

router = APIRouter(tags=["v4", "prompt templates"])


@router.get("/", response_model=PromptTemplateResponseList)
async def get_prompt_templates(service: PromptTemplateServiceDep) -> PromptTemplateResponseList:
    """Get list of available prompt templates"""
    return await asyncio.to_thread(service.get_prompt_templates_list)
