"""
Model Config Admin Router (FastAPI) - V4
-----------------------------------------

FastAPI router for administrative model configuration operations.
Converted from Flask blueprint in model_config_admin_blueprint.py.

All endpoints require the "write:model-config" permission.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import Response

from src.auth.fastapi_dependencies import Token, require_token_with_scope
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

logger = logging.getLogger(__name__)


def get_session_maker(request: Request) -> Any:
    """Get SQLAlchemy session maker from app state"""
    return request.app.state.session_maker


@router.get("/", response_model=AdminModelResponse)
async def get_admin_models(
    request: Request,
    _token: Token = Depends(require_token_with_scope("write:model-config")),
) -> AdminModelResponse:
    """Get full details of all models (admin endpoint)"""
    session_maker = get_session_maker(request)
    return get_model_configs_admin(session_maker)


@router.post("/", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def add_model(
    request: Request,
    model_request: RootCreateModelConfigRequest = Body(...),
    token: Token = Depends(require_token_with_scope("write:model-config")),
) -> ResponseModel:
    """Add a new model"""
    session_maker = get_session_maker(request)
    new_model = create_model_config(model_request, session_maker)

    logger.info({
        "event": "model_config.create",
        "user": token.token.sub if hasattr(token.token, "sub") else token.client,
        "request": model_request.model_dump(),
        "date": datetime.now(UTC),
    })

    return new_model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    request: Request,
    model_id: str,
    token: Token = Depends(require_token_with_scope("write:model-config")),
) -> Response:
    """Delete a model"""
    session_maker = get_session_maker(request)

    try:
        delete_model_config(model_id, session_maker)
        logger.info({
            "event": "model_config.delete",
            "user": token.token.sub if hasattr(token.token, "sub") else token.client,
            "model_id": model_id,
            "date": datetime.now(UTC),
        })
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        not_found_message = f"No model found with ID {model_id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_message) from e


@router.put("/", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_model(
    request: Request,
    reorder_request: ReorderModelConfigRequest = Body(...),
    token: Token = Depends(require_token_with_scope("write:model-config")),
) -> Response:
    """Reorder models"""
    session_maker = get_session_maker(request)

    try:
        reorder_model_config(reorder_request, session_maker)
        logger.info({
            "event": "model_config.reorder",
            "user": token.token.sub if hasattr(token.token, "sub") else token.client,
            "request": reorder_request.model_dump(),
            "date": datetime.now(UTC),
        })
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.put("/{model_id}", response_model=ResponseModel)
async def update_model(
    request: Request,
    model_id: str,
    update_request: RootUpdateModelConfigRequest = Body(...),
    token: Token = Depends(require_token_with_scope("write:model-config")),
) -> ResponseModel:
    """Update a model"""
    session_maker = get_session_maker(request)
    updated_model = update_model_config(model_id, update_request, session_maker)

    if updated_model is None:
        not_found_message = f"No model found with ID {model_id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_message)

    logger.info({
        "event": "model_config.update",
        "user": token.token.sub if hasattr(token.token, "sub") else token.client,
        "request": {**update_request.model_dump(), "model_id": model_id},
        "date": datetime.now(UTC),
    })

    return updated_model
