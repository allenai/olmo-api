from datetime import UTC, datetime

import structlog
from fastapi import APIRouter

from api.auth.permission_service import PermissionServiceDependency
from api.model_config.admin.model_config_admin_create_service import (
    ModelConfigCreateServiceDependency,
    RootCreateModelConfigRequest,
)
from api.model_config.admin.model_config_admin_read_service import (
    ModelConfigAdminReadServiceDependency,
)
from api.model_config.model_config_response import ModelConfigListResponse, ModelConfigResponse
from core.auth import Permissions

model_config_admin_router = APIRouter(prefix="/models")

logger = structlog.getLogger()


@model_config_admin_router.get("/")
async def get_admin_models(
    model_config_admin_service: ModelConfigAdminReadServiceDependency,
    permission_service: PermissionServiceDependency,
) -> ModelConfigListResponse:
    permission_service.require_permission(Permissions.WRITE_MODEL_CONFIG)

    return await model_config_admin_service.get_all()


@model_config_admin_router.post("/")
async def create_admin_model(
    request: RootCreateModelConfigRequest,
    model_config_admin_create_service: ModelConfigCreateServiceDependency,
    permission_service: PermissionServiceDependency,
) -> ModelConfigResponse:
    token = permission_service.require_permission(Permissions.WRITE_MODEL_CONFIG)

    new_model = await model_config_admin_create_service.create(request)

    logger.info(
        "model_config.create",
        user=token.client,
        date=datetime.now(UTC),
    )

    return new_model
