"""
V4 API Router (FastAPI)
-----------------------

Main router for v4 API endpoints.
Includes all v4 routers converted from Flask blueprints.
"""

from fastapi import APIRouter

from src.message.v4_message_router import router as message_router
from src.model_config.model_config_admin_router import router as admin_models_router
from src.model_config.model_config_router import router as models_router
from src.prompt_template.prompt_template_router import router as prompt_template_router
from src.thread.threads_router import router as threads_router
from src.transcription.transcription_router import router as transcription_router
from src.user.v4_user_router import router as user_router


def create_v4_router() -> APIRouter:
    """Create v4 API router with all sub-routers"""
    v4_router = APIRouter(prefix="/v4")

    # Message endpoints
    v4_router.include_router(message_router, prefix="/message")

    # Model configuration endpoints
    v4_router.include_router(models_router, prefix="/models")
    v4_router.include_router(admin_models_router, prefix="/admin/models")

    # Thread endpoints
    v4_router.include_router(threads_router, prefix="/threads")

    # Transcription endpoints
    v4_router.include_router(transcription_router, prefix="/transcribe")

    # Prompt template endpoints
    v4_router.include_router(prompt_template_router, prefix="/prompt-templates")

    # User endpoints
    v4_router.include_router(user_router)

    return v4_router
