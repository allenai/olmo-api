"""
V3 Templates (Prompts) Router (FastAPI)
----------------------------------------

FastAPI router for V3 template/prompt operations.
Converted from Flask blueprint in v3.py.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, status

from src.auth.fastapi_dependencies import RequiredAuth
from src.dependencies import DBClient

router = APIRouter(tags=["v3", "templates"])


@router.get("/prompts")
async def list_prompts(
    dbc: DBClient,
    deleted: bool = Query(False),
) -> Any:
    """Get list of prompt templates"""
    return await asyncio.to_thread(dbc.template.prompts, deleted=deleted)


@router.get("/prompt/{id}")
async def get_prompt(
    dbc: DBClient,
    id: str,
) -> Any:
    """Get a specific prompt template by ID"""
    prompt = await asyncio.to_thread(dbc.template.prompt, id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return prompt


@router.post("/prompt", status_code=status.HTTP_201_CREATED)
async def create_prompt(
    dbc: DBClient,
    token: RequiredAuth,
    body: dict = Body(...),
) -> Any:
    """Create a new prompt template"""
    name = body.get("name")
    content = body.get("content")

    if not name or not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide name and content"
        )

    prompt = await asyncio.to_thread(dbc.template.create_prompt, name, content, token.client)
    return prompt


@router.patch("/prompt/{id}")
async def update_prompt(
    dbc: DBClient,
    token: RequiredAuth,
    id: str,
    body: dict = Body(...),
) -> Any:
    """Update an existing prompt template"""
    prompt = await asyncio.to_thread(dbc.template.prompt, id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    if prompt.author != token.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    updated_prompt = await asyncio.to_thread(
        dbc.template.update_prompt,
        id,
        body.get("name"),
        body.get("content"),
        body.get("deleted"),
    )

    if updated_prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    return updated_prompt


@router.delete("/prompt/{id}")
async def delete_prompt(
    dbc: DBClient,
    token: RequiredAuth,
    id: str,
) -> Any:
    """Delete a prompt template (soft delete)"""
    prompt = await asyncio.to_thread(dbc.template.prompt, id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    if prompt.author != token.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return await asyncio.to_thread(dbc.template.update_prompt, id, deleted=True)
