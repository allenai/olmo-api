"""
V3 Labels Router (FastAPI)
---------------------------

FastAPI router for V3 label operations (message ratings and feedback).
Converted from Flask blueprint in v3.py.
"""

import io
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from src import db, util
from src.auth.fastapi_dependencies import RequiredAuth
from src.dao import label, paged
from src.dao.fastapi_sqlalchemy_session import DBSession
from src.dao.message.message_repository import MessageRepository

router = APIRouter(tags=["v3", "labels"])


def get_db_client(request: Request) -> db.Client:
    """Get psycopg3 database client from app state"""
    return request.app.state.dbc


@router.get("/labels")
async def list_labels(
    request: Request,
    message: str | None = Query(None),
    creator: str | None = Query(None),
    rating: int | None = Query(None),
    deleted: bool = Query(False),
    export: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1_000_000),
) -> Any:
    """Get list of labels with optional filtering"""
    dbc = get_db_client(request)

    try:
        rating_enum = label.Rating(rating) if rating is not None else None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    opts = paged.Opts(offset=offset, limit=limit)

    ll = dbc.label.get_list(
        message=message,
        creator=creator,
        deleted=deleted,
        rating=rating_enum,
        opts=opts,
    )

    # Export to JSONL file
    if export:
        labels_jsonl = "\n".join([json.dumps(lbl, cls=util.CustomEncoder) for lbl in ll.labels])
        filename = f"labels-{int(datetime.now(UTC).timestamp())}.jsonl"

        return StreamingResponse(
            io.BytesIO(labels_jsonl.encode("utf-8")),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    return ll


@router.get("/label/{id}")
async def get_label(
    request: Request,
    id: str,
) -> Any:
    """Get a specific label by ID"""
    dbc = get_db_client(request)
    lbl = dbc.label.get(id)
    if lbl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")
    return lbl


@router.post("/label", status_code=status.HTTP_201_CREATED)
async def create_label(
    request: Request,
    session: DBSession,
    token: RequiredAuth,
    body: dict = Body(...),
) -> Any:
    """Create a new label for a message"""
    dbc = get_db_client(request)

    message_id = body.get("message")
    if not message_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide message ID"
        )

    # Check if message exists
    message_repository = MessageRepository(session)
    msg = message_repository.get_message_by_id(message_id)
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message {message_id} not found"
        )

    # Validate rating
    try:
        rating_value = label.Rating(body.get("rating"))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Check for existing label
    existing = dbc.label.get_list(
        message=message_id,
        creator=token.client,
    )
    if existing.meta.total != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Message {message_id} already has label {existing.labels[0].id}"
        )

    lbl = dbc.label.create(msg.id, rating_value, token.client, body.get("comment"))
    return lbl


@router.delete("/label/{id}")
async def delete_label(
    request: Request,
    token: RequiredAuth,
    id: str,
) -> Any:
    """Delete a label (soft delete)"""
    dbc = get_db_client(request)

    lbl = dbc.label.get(id)
    if lbl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")

    if lbl.creator != token.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    deleted = dbc.label.delete(id)
    if deleted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")

    return deleted
