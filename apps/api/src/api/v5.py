from fastapi import APIRouter

from api.config import settings
from api.event import event_router
from api.model_config.admin.model_config_admin_router import model_config_admin_router

v5_router = APIRouter(prefix="/v5")


v5_router.include_router(event_router)

if not settings.ENV.is_production:
    v5_router.include_router(model_config_admin_router)
