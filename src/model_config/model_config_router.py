"""
Model Config Router (FastAPI)
------------------------------

FastAPI router for model configuration endpoints.
Converted from Flask blueprint in model_config_blueprint.py.
"""

import asyncio

from fastapi import APIRouter

from src.auth.auth_utils import Permissions, user_has_permission
from src.auth.fastapi_dependencies import OptionalAuth
from src.dependencies import SessionFactory
from src.model_config.get_model_config_service import ModelResponse, get_model_configs

router = APIRouter(tags=["v4", "models"])


@router.get("/", response_model=ModelResponse)
async def get_models(
    session_maker: SessionFactory,
    token: OptionalAuth = None,
) -> ModelResponse:
    """
    Get list of available models.

    Internal models are filtered based on user permissions.
    Anonymous users only see public models.
    """
    should_include_internal_models = user_has_permission(token.token if token else None, Permissions.READ_INTERNAL_MODELS)

    return await asyncio.to_thread(
        get_model_configs,
        session_maker=session_maker,
        include_internal_models=should_include_internal_models,
    )
