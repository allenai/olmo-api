"""
Model Config Admin Router (FastAPI) - V4
-----------------------------------------

FastAPI router for administrative model configuration operations.
Converted from Flask blueprint in model_config_admin_blueprint.py.

All endpoints require the "write:model-config" permission.
"""

import asyncio
import structlog
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import Response

from src.auth.fastapi_dependencies import Token, require_token_with_scope
from src.dependencies import SessionFactory
from src.model_config.create_model_config_service import (
    ResponseModel,
    RootCreateModelConfigRequest,
    create_model_config,
)
from src.model_config.delete_model_config_service import (
    delete_model_config,
)
from src.model_config.get_model_config_service import (
    AdminModelResponse,
    get_model_configs_admin,
)
from src.model_config.reorder_model_config_service import (
    ReorderModelConfigRequest,
    reorder_model_config,
)
from src.model_config.update_model_config_service import (
    RootUpdateModelConfigRequest,
    update_model_config,
)

router = APIRouter(tags=["v4", "models", "model configuration"])

logger = structlog.get_logger(__name__)


@router.get("/", response_model=AdminModelResponse)
async def get_admin_models(
    session_maker: SessionFactory,
    _token: Token = Depends(require_token_with_scope("write:model-config")),
) -> AdminModelResponse:
    """Get full details of all models (admin endpoint)"""
    return await asyncio.to_thread(get_model_configs_admin, session_maker)


@router.post("/", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def add_model(
    session_maker: SessionFactory,
    model_request: RootCreateModelConfigRequest = Body(...),
    token: Token = Depends(require_token_with_scope("write:model-config")),
) -> ResponseModel:
    """Add a new model"""
    new_model = await asyncio.to_thread(create_model_config, model_request, session_maker)

    logger.info(
        "model_config_create",
        user=token.token.sub if hasattr(token.token, "sub") else token.client,
        request=model_request.model_dump(),
        date=datetime.now(UTC),
    )

    return new_model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    session_maker: SessionFactory,
    model_id: str,
    token: Token = Depends(require_token_with_scope("write:model-config")),
) -> Response:
    """Delete a model"""
    try:
        await asyncio.to_thread(delete_model_config, model_id, session_maker)
        logger.info(
            "model_config_delete",
            user=token.token.sub if hasattr(token.token, "sub") else token.client,
            model_id=model_id,
            date=datetime.now(UTC),
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        not_found_message = f"No model found with ID {model_id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_message) from e


@router.put("/", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_model(
    session_maker: SessionFactory,
    reorder_request: ReorderModelConfigRequest = Body(...),
    token: Token = Depends(require_token_with_scope("write:model-config")),
) -> Response:
    """Reorder models"""
    try:
        await asyncio.to_thread(reorder_model_config, reorder_request, session_maker)
        logger.info(
            "model_config_reorder",
            user=token.token.sub if hasattr(token.token, "sub") else token.client,
            request=reorder_request.model_dump(),
            date=datetime.now(UTC),
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.put("/{model_id}", response_model=ResponseModel)
async def update_model(
    session_maker: SessionFactory,
    model_id: str,
    update_request: RootUpdateModelConfigRequest = Body(...),
    token: Token = Depends(require_token_with_scope("write:model-config")),
) -> ResponseModel:
    """Update a model"""
    updated_model = await asyncio.to_thread(update_model_config, model_id, update_request, session_maker)

    if updated_model is None:
        not_found_message = f"No model found with ID {model_id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_message)

    logger.info(
        "model_config_update",
        user=token.token.sub if hasattr(token.token, "sub") else token.client,
        request={**update_request.model_dump(), "model_id": model_id},
        date=datetime.now(UTC),
    )

    return updated_model
