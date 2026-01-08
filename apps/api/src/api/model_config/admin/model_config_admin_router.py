from fastapi import APIRouter

from api.model_config.admin.model_config_admin_service import (
    AdminModelResponse,
    ModelConfigAdminServiceDependency,
)

model_config_admin_router = APIRouter(prefix="/admin")


@model_config_admin_router.get("/")
async def get_admin_models(
    model_config_admin_service: ModelConfigAdminServiceDependency,
) -> AdminModelResponse:
    return await model_config_admin_service.get_all()
