"""
V3 Templates (Prompts) Router (FastAPI)
----------------------------------------

FastAPI router for V3 template/prompt operations.
Converted from Flask blueprint in v3.py.
"""

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request, status

from src import db
from src.auth.fastapi_dependencies import RequiredAuth

router = APIRouter(tags=["v3", "templates"])


def get_db_client(request: Request) -> db.Client:
    """Get psycopg3 database client from app state"""
    return request.app.state.dbc


@router.get("/prompts")
async def list_prompts(
    request: Request,
    deleted: bool = Query(False),
) -> Any:
    """Get list of prompt templates"""
    dbc = get_db_client(request)
    return dbc.template.prompts(deleted=deleted)


@router.get("/prompt/{id}")
async def get_prompt(
    request: Request,
    id: str,
) -> Any:
    """Get a specific prompt template by ID"""
    dbc = get_db_client(request)
    prompt = dbc.template.prompt(id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return prompt


@router.post("/prompt", status_code=status.HTTP_201_CREATED)
async def create_prompt(
    request: Request,
    token: RequiredAuth,
    body: dict = Body(...),
) -> Any:
    """Create a new prompt template"""
    dbc = get_db_client(request)

    name = body.get("name")
    content = body.get("content")

    if not name or not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide name and content"
        )

    prompt = dbc.template.create_prompt(name, content, token.client)
    return prompt


@router.patch("/prompt/{id}")
async def update_prompt(
    request: Request,
    token: RequiredAuth,
    id: str,
    body: dict = Body(...),
) -> Any:
    """Update an existing prompt template"""
    dbc = get_db_client(request)

    prompt = dbc.template.prompt(id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    if prompt.author != token.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    updated_prompt = dbc.template.update_prompt(
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
    request: Request,
    token: RequiredAuth,
    id: str,
) -> Any:
    """Delete a prompt template (soft delete)"""
    dbc = get_db_client(request)

    prompt = dbc.template.prompt(id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    if prompt.author != token.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return dbc.template.update_prompt(id, deleted=True)
