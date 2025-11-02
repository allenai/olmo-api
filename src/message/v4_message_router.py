"""
Message Router (FastAPI) - V4
------------------------------

FastAPI router for message creation with streaming support.
Converted from Flask blueprint in v4_message_blueprint.py.
"""

import asyncio
from collections.abc import Generator
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.auth.fastapi_dependencies import RequiredAuth
from src.dao.engine_models.message import Message as SQLAMessage
from src.dao.message.message_repository import MessageRepository, map_sqla_to_old
from src.dependencies import DBClient, StorageClient
from src.message.create_message_request import CreateMessageRequest
from src.message.create_message_service.endpoint import (
    MessageCreationServiceDep,
    create_message_v4,
    format_message,
)

router = APIRouter(tags=["v4", "message"])


def format_messages(stream_generator: Generator) -> Generator[str, Any, None]:
    """Format stream messages for JSONL output"""
    for message in stream_generator:
        match message:
            case SQLAMessage():
                # map Message to old message...
                yield format_message(map_sqla_to_old(message))
            case _:
                yield format_message(message)


@router.post("/stream", response_model=None)
async def create_message(
    request: Request,
    dbc: DBClient,
    storage: StorageClient,
    service: MessageCreationServiceDep,
    token: RequiredAuth,
    # Form fields
    content: str = Form(...),
    model: str = Form(...),
    host: str = Form(...),
    parent: str | None = Form(None),
    role: str | None = Form(None),
    original: str | None = Form(None),
    private: bool = Form(False),
    template: str | None = Form(None),
    tool_call_id: str | None = Form(None),
    tool_definitions: str | None = Form(None),  # JSON string (Pydantic will parse)
    selected_tools: str | None = Form(None),  # JSON string (Pydantic will parse)
    enable_tool_calling: bool = Form(False),
    bypass_safety_check: bool = Form(False),
    captcha_token: str | None = Form(None),
    max_tokens: int | None = Form(None),
    temperature: float | None = Form(None),
    top_p: float | None = Form(None),
    stop: str | None = Form(None),  # JSON string (Pydantic will parse)
    n: int | None = Form(1),
    logprobs: int | None = Form(None),
    extra_parameters: str | None = Form(None),  # JSON string (Pydantic will parse)
    # File uploads
    files: list[UploadFile] | None = File(None),
) -> StreamingResponse | Any:
    """
    Create a new message with streaming response.

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

    # Call service in thread pool to avoid blocking event loop
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
