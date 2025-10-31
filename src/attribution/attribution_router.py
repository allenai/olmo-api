"""
Attribution Router (FastAPI) - V3
----------------------------------

FastAPI router for attribution (CorpusLink) operations.
Converted from Flask blueprint in attribution_blueprint.py.
"""

from typing import Any

from fastapi import APIRouter, Body, HTTPException, status

from src.attribution.attribution_service import GetAttributionRequest, get_attribution
from src.attribution.infini_gram_api_client import Client
from src.config.get_config import cfg
from src.dao.fastapi_sqlalchemy_session import DBSession
from src.model_config.get_model_config_service import get_single_model_config_admin

router = APIRouter(tags=["v3", "CorpusLink"])


@router.post("")
async def get_attribution_for_model_response(
    session: DBSession,
    corpuslink_request: GetAttributionRequest = Body(...),
) -> Any:
    """Get CorpusLink spans and documents from a prompt"""
    config = get_single_model_config_admin(session, corpuslink_request.model_id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    if config.infini_gram_index is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model {config.id} does not have an infini gram index configured"
        )

    infini_gram_client = Client(base_url=cfg.infini_gram.api_url, raise_on_unexpected_status=True)

    attribution_response = get_attribution(
        request=corpuslink_request, infini_gram_client=infini_gram_client, model_config=config
    )

    return attribution_response
