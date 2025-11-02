"""
Prompt Template Router (FastAPI) - V4
--------------------------------------

FastAPI router for prompt template operations.
Converted from Flask blueprint in prompt_template_blueprint.py.
"""

import asyncio

from fastapi import APIRouter

from src.dependencies import DBSession
from src.prompt_template.prompt_template_models import PromptTemplateResponseList
from src.prompt_template.prompt_template_service import get_prompt_templates_list

router = APIRouter(tags=["v4", "prompt templates"])


@router.get("/", response_model=PromptTemplateResponseList)
async def get_prompt_templates(session: DBSession) -> PromptTemplateResponseList:
    """Get list of available prompt templates"""
    return await asyncio.to_thread(get_prompt_templates_list, session)
