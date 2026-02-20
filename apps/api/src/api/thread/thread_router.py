from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from api.auth.auth_service import AuthServiceDependency
from api.service_errors import ForbiddenError, NotFoundError
from api.thread.chat.chat_service import ChatRequest, ChatServiceDependency
from api.thread.chat.format_output import format_messages
from api.thread.models.thread import Thread, ThreadList
from api.thread.thread_delete_service import ThreadDeleteServiceDependency
from api.thread.thread_read_service import ThreadReadServiceDependency
from core.sort_options import SortOptions

SortOptionsParams = Annotated[SortOptions, Query()]

thread_router = APIRouter(prefix="/threads")


@thread_router.get("/")
async def get_all(
    sort_options: SortOptionsParams,
    thread_read_service: ThreadReadServiceDependency,
    auth_service: AuthServiceDependency,
) -> ThreadList:
    token = auth_service.optional_auth()
    threads = await thread_read_service.get_all_for_user(user_id=token.client, sort_options=sort_options)
    return threads


@thread_router.get("/{thread_id}")
async def get_one_with_async_attrs(
    thread_id: str,
    thread_read_service: ThreadReadServiceDependency,
    auth_service: AuthServiceDependency,
) -> Thread:
    token = auth_service.optional_auth()
    thread = await thread_read_service.get_one_with_user(thread_id=thread_id, user_id=token.client)

    if thread is None:
        not_found_message = f"No thread found with ID `{thread_id}`"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_message)

    return thread


@thread_router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str, thread_delete_service: ThreadDeleteServiceDependency, auth_service: AuthServiceDependency
):
    token = auth_service.optional_auth()
    try:
        await thread_delete_service.delete(thread_id=thread_id, user=token)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@thread_router.post("/chat")
async def stream_chat_message(
    chat_service: ChatServiceDependency,
    auth_service: AuthServiceDependency,
    request: ChatRequest = Form(),  # noqa: B008
):
    token = auth_service.optional_auth()

    # TODO: Figure out why errors here don't return properly
    return StreamingResponse(
        format_messages(chat_service.stream_chat_message(request, user=token)), media_type="application/jsonl"
    )
