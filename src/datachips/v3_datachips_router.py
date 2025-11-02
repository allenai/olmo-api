"""
V3 Datachips Router (FastAPI)
------------------------------

FastAPI router for V3 datachip operations (user data storage).
Converted from Flask blueprint in v3.py.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, status

from src.auth.fastapi_dependencies import RequiredAuth
from src.dao import datachip, paged
from src.dependencies import DBClient

router = APIRouter(tags=["v3", "datachips"])


@router.get("/datachips")
async def list_datachips(
    dbc: DBClient,
    creator: str | None = Query(None),
    deleted: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
) -> Any:
    """Get list of datachips with optional filtering"""
    opts = paged.Opts(offset=offset, limit=limit)

    return await asyncio.to_thread(
        dbc.datachip.list_all,
        creator=creator,
        deleted=deleted,
        opts=opts,
    )


@router.get("/datachip/{id}")
async def get_datachip(
    dbc: DBClient,
    id: str,
) -> Any:
    """Get a specific datachip by ID"""
    chips = await asyncio.to_thread(dbc.datachip.get, [id])
    if len(chips) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datachip not found")
    if len(chips) > 1:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Multiple datachips with same ID"
        )

    return chips[0]


@router.post("/datachip", status_code=status.HTTP_201_CREATED)
async def create_datachip(
    dbc: DBClient,
    token: RequiredAuth,
    body: dict = Body(...),
) -> Any:
    """Create a new datachip"""
    name = body.get("name", "").strip()
    if name == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify a non-empty name"
        )

    content = body.get("content", "").strip()
    if content == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify non-empty content"
        )

    if len(content.encode("utf-8")) > 500 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Content must be < 500MB"
        )

    return await asyncio.to_thread(dbc.datachip.create, name, content, token.client)


@router.patch("/datachip/{id}")
async def update_datachip(
    dbc: DBClient,
    token: RequiredAuth,
    id: str,
    body: dict = Body(...),
) -> Any:
    """Update a datachip (currently only supports soft delete)"""
    chips = await asyncio.to_thread(dbc.datachip.get, [id])
    if len(chips) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datachip not found")
    if len(chips) > 1:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Multiple datachips with same ID"
        )

    chip = chips[0]
    if chip.creator != token.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    deleted = body.get("deleted")
    updated = await asyncio.to_thread(dbc.datachip.update, id, datachip.Update(deleted))
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datachip not found")

    return updated
