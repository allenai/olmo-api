"""
Attribution Router (FastAPI) - V3
----------------------------------

FastAPI router for attribution (CorpusLink) operations.
Converted from Flask blueprint in attribution_blueprint.py.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, status

from src.attribution.attribution_service import GetAttributionRequest, get_attribution
from src.attribution.infini_gram_api_client import Client
from src.dependencies import AppConfig
from src.model_config.get_model_config_service import ModelConfigServiceDep

router = APIRouter(tags=["v3", "CorpusLink"])


@router.post("")
async def get_attribution_for_model_response(
    model_service: ModelConfigServiceDep,
    config: AppConfig,
    corpuslink_request: GetAttributionRequest = Body(...),
) -> Any:
    """Get CorpusLink spans and documents from a prompt"""
    model_config = await asyncio.to_thread(
        model_service.get_by_id, corpuslink_request.model_id
    )
    if model_config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    if model_config.infini_gram_index is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model {model_config.id} does not have an infini gram index configured"
        )

    infini_gram_client = Client(base_url=config.infini_gram.api_url, raise_on_unexpected_status=True)

    attribution_response = await asyncio.to_thread(
        get_attribution,
        request=corpuslink_request,
        infini_gram_client=infini_gram_client,
        model_config=model_config
    )

    return attribution_response
