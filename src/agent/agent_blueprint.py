import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import AnyStr

from flask import Blueprint, Response, stream_with_context
from pydantic import ValidationError

from src import db
from src.agent.agent_stream_service import AgentChatRequest, get_agent_stream_adapter
from src.auth.resource_protectors import anonymous_auth_protector
from src.error import handle_validation_error
from src.flask_pydantic_api.api_wrapper import pydantic_api
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.pydantic_ai.ui.playground_ui._event_stream import JSONL_CONTENT_TYPE


def iter_over_async(async_iterator: AsyncIterator) -> Iterator[AnyStr]:
    loop = asyncio.new_event_loop()
    ait = aiter(async_iterator)

    async def get_next():
        try:
            obj = await anext(ait)
            return False, obj
        except StopAsyncIteration:
            return True, None

    while True:
        done, obj = loop.run_until_complete(get_next())
        if done:
            break
        yield obj  # type: ignore


def create_agents_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage) -> Blueprint:
    agents_blueprint = Blueprint(name="agents", import_name=__name__)

    @agents_blueprint.post("/chat")
    @anonymous_auth_protector()
    @pydantic_api(name="Stream a chat agent response", tags=["v4", "agents"])
    def stream_chat_agent_response(request: AgentChatRequest):
        try:
            stream_adapter = get_agent_stream_adapter(request=request, dbc=dbc, storage_client=storage_client)
            event_stream = stream_adapter.run_stream()

            sync_iterator = iter_over_async(stream_adapter.encode_stream(event_stream))
            return Response(stream_with_context(sync_iterator), content_type=JSONL_CONTENT_TYPE)

        except ValidationError as e:
            return handle_validation_error(e)

    return agents_blueprint
