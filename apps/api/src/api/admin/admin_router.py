from fastapi import APIRouter

from api.model_config.admin.model_config_admin_router import model_config_admin_router

admin_router = APIRouter(prefix="/admin")

admin_router.include_router(model_config_admin_router)
