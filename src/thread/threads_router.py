"""
Threads Router (FastAPI) - V4
------------------------------

FastAPI router for thread/conversation management.
Converted from Flask blueprint in threads_blueprint.py.
"""

import asyncio
from collections.abc import Generator
from logging import getLogger
from typing import Any

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.api_interface import APIInterface
from src.auth.fastapi_dependencies import RequiredAuth
from src.dao.engine_models.message import Message
from src.dao.message import message_models
from src.dao.message.message_repository import MessageRepository
from src.dependencies import DBClient, DBSession, StorageClient
from src.message.create_message_request import CreateMessageRequest
from src.message.create_message_service.endpoint import (
    MessageCreationServiceDep,
    create_message_v4,
    format_message,
)
from src.message.message_chunk import Chunk
from src.thread.get_thread_service import get_thread
from src.thread.get_threads_service import GetThreadsRequest, GetThreadsResponse, get_threads
from src.thread.thread_models import Thread

router = APIRouter(tags=["v4", "threads"])


def format_messages(
    stream_generator: Generator[Message | message_models.MessageChunk | message_models.MessageStreamError | Chunk],
) -> Generator[str, Any, None]:
    """Format stream messages for JSONL output"""
    try:
        for stream_message in stream_generator:
            match stream_message:
                case Message():
                    flat_messages = Thread.from_message(stream_message)
                    yield format_message(flat_messages)
                case APIInterface():
                    yield format_message(stream_message)
    except Exception:
        getLogger().exception("Error when streaming")
        raise


@router.get("/", response_model=GetThreadsResponse)
async def list_threads(
    session: DBSession,
    token: RequiredAuth,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    order: str = Query("desc", pattern="^(asc|desc)$"),
) -> GetThreadsResponse:
    """
    Get list of threads for authenticated user.

    Query parameters:
    - offset: Number of items to skip (default: 0)
    - limit: Number of items to return (default: 50, max: 100)
    - order: Sort order - "asc" or "desc" (default: "desc")
    """
    request = GetThreadsRequest(offset=offset, limit=limit, order=order)  # type: ignore
    return get_threads(request, message_repository=MessageRepository(session), token=token)


@router.get("/{thread_id}", response_model=Thread)
async def get_single_thread(
    thread_id: str,
    session: DBSession,
    token: RequiredAuth,
) -> Thread:
    """Get specific thread by ID"""
    return get_thread(thread_id, user_id=token.client, message_repository=MessageRepository(session))


@router.post("/", response_model=None)
async def create_message_in_thread(
    request: Request,
    dbc: DBClient,
    storage: StorageClient,
    service: MessageCreationServiceDep,
    token: RequiredAuth,
    # Form fields - same as message router
    content: str = Form(...),
    model: str = Form(...),
    host: str = Form(...),
    parent: str | None = Form(None),
    role: str | None = Form(None),
    original: str | None = Form(None),
    private: bool = Form(False),
    template: str | None = Form(None),
    tool_call_id: str | None = Form(None),
    tool_definitions: str | None = Form(None),
    selected_tools: str | None = Form(None),
    enable_tool_calling: bool = Form(False),
    bypass_safety_check: bool = Form(False),
    captcha_token: str | None = Form(None),
    max_tokens: int | None = Form(None),
    temperature: float | None = Form(None),
    top_p: float | None = Form(None),
    stop: str | None = Form(None),
    n: int | None = Form(1),
    logprobs: int | None = Form(None),
    extra_parameters: str | None = Form(None),
    files: list[UploadFile] | None = File(None),
) -> StreamingResponse | Any:
    """
    Create a new message in a thread with streaming response.

    Accepts multipart/form-data with optional file uploads.
    Returns JSONL stream of message chunks.
    """
    # Convert FastAPI UploadFile to Werkzeug FileStorage
    from werkzeug.datastructures import FileStorage

    uploaded_files = None
    if files:
        uploaded_files = []
        for file in files:
            file_storage = FileStorage(
                stream=file.file,
                filename=file.filename,
                name=file.filename,
                content_type=file.content_type,
            )
            uploaded_files.append(file_storage)

    # Build request object - exclude role if None to use default
    # JSON fields are passed as strings and will be parsed by Pydantic's Json[] type
    request_kwargs = {
        "parent": parent,
        "content": content,
        "original": original,
        "private": private,
        "template": template,
        "model": model,
        "host": host,
        "tool_call_id": tool_call_id,
        "tool_definitions": tool_definitions,  # Pydantic parses JSON
        "selected_tools": selected_tools,  # Pydantic parses JSON
        "enable_tool_calling": enable_tool_calling,
        "bypass_safety_check": bypass_safety_check,
        "captcha_token": captcha_token,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stop": stop,  # Pydantic parses JSON
        "n": n,
        "logprobs": logprobs,
        "extra_parameters": extra_parameters,  # Pydantic parses JSON
        "files": uploaded_files,
    }
    if role is not None:
        request_kwargs["role"] = role  # type: ignore

    create_message_request = CreateMessageRequest(**request_kwargs)

    # Call service (wrapped in asyncio.to_thread to avoid blocking)
    stream_response = await asyncio.to_thread(
        service.create_message,
        create_message_request,
        dbc,
        storage_client=storage,
        message_repository=MessageRepository(service.session),
        token=token,
        user_ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    if isinstance(stream_response, Generator):
        # Streaming response
        return StreamingResponse(
            format_messages(stream_response),
            media_type="application/jsonl",
        )

    # Non-streaming response
    return stream_response
