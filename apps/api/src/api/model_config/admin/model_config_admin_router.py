from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from api.auth.permission_service import PermissionServiceDependency
from api.logging.fastapi_logger import FastAPIStructLogger
from api.model_config.admin.model_config_admin_create_service import (
    ModelConfigCreateServiceDependency,
    RootCreateModelConfigRequest,
)
from api.model_config.admin.model_config_admin_read_service import (
    ModelConfigAdminReadServiceDependency,
)
from api.model_config.admin.model_config_admin_update_service import (
    ModelConfigUpdateServiceDependency,
    RootUpdateModelConfigRequest,
)
from api.model_config.model_config_response import ModelConfigListResponse, ModelConfigResponse
from core.auth import Permissions

model_config_admin_router = APIRouter(prefix="/models")

logger = FastAPIStructLogger()


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
        request={**request.model_dump()},
        date=datetime.now(UTC),
    )

    return new_model


@model_config_admin_router.put("/{model_id}")
async def update_admin_model(
    model_id: str,
    request: RootUpdateModelConfigRequest,
    model_config_admin_update_service: ModelConfigUpdateServiceDependency,
    permission_service: PermissionServiceDependency,
) -> ModelConfigResponse | None:
    token = permission_service.require_permission(Permissions.WRITE_MODEL_CONFIG)

    try:
        updated_model = await model_config_admin_update_service.update(model_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)) from e

    if updated_model is None:
        not_found_message = f"No model found with ID {model_id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_message)

    logger.info(
        "model_config.update",
        user=token.client,
        model_id=model_id,
        request={**request.model_dump()},
        date=datetime.now(UTC),
    )

    return updated_model
