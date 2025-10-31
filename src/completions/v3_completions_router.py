"""
V3 Completions Router (FastAPI)
--------------------------------

FastAPI router for V3 completion operations (admin only).
Converted from Flask blueprint in v3.py.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from src import db
from src.auth.fastapi_dependencies import RequiredAuth
from src.config import get_config

router = APIRouter(tags=["v3", "completions"])


def get_db_client(request: Request) -> db.Client:
    """Get psycopg3 database client from app state"""
    return request.app.state.dbc


@router.get("/completion/{id}")
async def get_completion(
    request: Request,
    token: RequiredAuth,
    id: str,
) -> Any:
    """
    Get a completion by ID (admin only).

    Only admins can view completions, since they might be related to private messages.
    """
    dbc = get_db_client(request)

    # TODO: OEUI-141 we need to use Auth0 permissions instead of checking this list
    if token.client not in get_config.cfg.server.admins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    completion = dbc.completion.get(id)
    if completion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Completion not found")

    return completion
