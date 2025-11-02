"""
V3 Completions Router (FastAPI)
--------------------------------

FastAPI router for V3 completion operations (admin only).
Converted from Flask blueprint in v3.py.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, status

from src.auth.fastapi_dependencies import RequiredAuth
from src.config import get_config
from src.dependencies import DBClient

router = APIRouter(tags=["v3", "completions"])


@router.get("/completion/{id}")
async def get_completion(
    dbc: DBClient,
    token: RequiredAuth,
    id: str,
) -> Any:
    """
    Get a completion by ID (admin only).

    Only admins can view completions, since they might be related to private messages.
    """
    # TODO: OEUI-141 we need to use Auth0 permissions instead of checking this list
    if token.client not in get_config.cfg.server.admins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    completion = await asyncio.to_thread(dbc.completion.get, id)
    if completion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Completion not found")

    return completion
