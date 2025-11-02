"""
V3 Message Router (FastAPI)
----------------------------

FastAPI router for V3 message operations (get, delete).
Converted from Flask blueprint in v3_message_blueprint.py.
"""

import asyncio
from typing import Any

from fastapi import APIRouter

from src.auth.fastapi_dependencies import RequiredAuth
from src.dependencies import DBClient, DBSession, StorageClient
from src.message.message_service import delete_message as delete_message_service
from src.message.message_service import get_message

router = APIRouter(tags=["v3", "message"])


@router.get("/{id}")
async def get_message_by_id(
    id: str,
    token: RequiredAuth,
    session: DBSession,
) -> Any:
    """Get a message by ID"""
    return await asyncio.to_thread(get_message, id=id, token=token, session=session)


@router.delete("/{id}")
async def delete_message(
    id: str,
    token: RequiredAuth,
    session: DBSession,
    dbc: DBClient,
    storage_client: StorageClient,
) -> Any:
    """Delete a message"""
    return await asyncio.to_thread(
        delete_message_service, id=id, dbc=dbc, storage_client=storage_client, token=token, session=session
    )
