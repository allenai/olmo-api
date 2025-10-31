"""
V3 API Router (FastAPI)
-----------------------

Main router for V3 API endpoints (legacy).
Includes all V3 routers converted from Flask blueprints.
"""

from fastapi import APIRouter

from src.attribution.attribution_router import router as attribution_router
from src.completions.v3_completions_router import router as completions_router
from src.datachips.v3_datachips_router import router as datachips_router
from src.labels.v3_labels_router import router as labels_router
from src.log.logging_router import router as logging_router
from src.message.v3_message_router import router as v3_message_router
from src.templates.v3_templates_router import router as templates_router
from src.user.v4_user_router import router as user_router


def create_v3_router() -> APIRouter:
    """Create V3 API router with all sub-routers"""
    v3_router = APIRouter(prefix="/v3")

    # Templates (prompts) endpoints
    v3_router.include_router(templates_router, prefix="/templates")

    # Labels endpoints
    v3_router.include_router(labels_router)

    # Completions endpoints
    v3_router.include_router(completions_router)

    # Datachips endpoints
    v3_router.include_router(datachips_router)

    # Message endpoints
    v3_router.include_router(v3_message_router, prefix="/message")

    # User endpoints (shared with V4)
    v3_router.include_router(user_router)

    # Attribution (CorpusLink) endpoints
    v3_router.include_router(attribution_router, prefix="/attribution")

    # Logging endpoints
    v3_router.include_router(logging_router, prefix="/log")

    return v3_router
