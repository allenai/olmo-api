from fastapi import APIRouter

from api.auth.auth_service import AuthServiceDependency
from api.auth.permission_service import PermissionServiceDependency
from api.model.model_read_service import ModelReadServiceDependency
from api.model.model_response import ModelListResponse
from core.auth import Permissions

model_router = APIRouter(prefix="/models", tags=["models"])


@model_router.get("/")
async def get_models(
    model_config_read_service: ModelReadServiceDependency,
    auth_service: AuthServiceDependency,
    permission_service: PermissionServiceDependency,
) -> ModelListResponse:
    """Get available models"""
    token = auth_service.optional_auth()
    should_include_internal_models = permission_service.has_permission(token, Permissions.READ_INTERNAL_MODELS)

    return await model_config_read_service.get_all(include_internal_models=should_include_internal_models)
