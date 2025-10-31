"""
V3 Message Router (FastAPI)
----------------------------

FastAPI router for V3 message operations (get, delete).
Converted from Flask blueprint in v3_message_blueprint.py.
"""

from typing import Any

from fastapi import APIRouter, Request

from src import db
from src.auth.fastapi_dependencies import RequiredAuth
from src.dao.fastapi_sqlalchemy_session import DBSession
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.message_service import delete_message as delete_message_service
from src.message.message_service import get_message

router = APIRouter(tags=["v3", "message"])


def get_db_client(request: Request) -> db.Client:
    """Get psycopg3 database client from app state"""
    return request.app.state.dbc


def get_storage_client(request: Request) -> GoogleCloudStorage:
    """Get storage client from app state"""
    return request.app.state.storage_client


@router.get("/{id}")
async def get_message_by_id(
    _request: Request,
    id: str,
    token: RequiredAuth,
    session: DBSession,
) -> Any:
    """Get a message by ID"""
    return get_message(id=id, token=token, session=session)


@router.delete("/{id}")
async def delete_message(
    request: Request,
    id: str,
    token: RequiredAuth,
    session: DBSession,
) -> Any:
    """Delete a message"""
    dbc = get_db_client(request)
    storage_client = get_storage_client(request)

    return delete_message_service(id=id, dbc=dbc, storage_client=storage_client, token=token, session=session)
