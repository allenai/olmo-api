from collections.abc import Generator
from logging import getLogger
from typing import Any

from flask import Blueprint, Response, jsonify, stream_with_context
from flask.typing import ResponseReturnValue
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

import src.dao.message.message_models as message
from src import db
from src.api_interface import APIInterface
from src.auth.auth_service import authn
from src.auth.resource_protectors import anonymous_auth_protector
from src.dao.engine_models.message import Message
from src.dao.flask_sqlalchemy_session import current_session
from src.dao.message.message_repository import MessageRepository
from src.error import handle_validation_error
from src.flask_pydantic_api.api_wrapper import pydantic_api
from src.message.create_message_request import CreateMessageRequest
from src.message.create_message_service.endpoint import create_message_v4, format_message
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.message_chunk import Chunk
from src.thread.get_thread_service import get_thread
from src.thread.get_threads_service import GetThreadsRequest, GetThreadsResponse, get_threads
from src.thread.thread_models import Thread


def format_messages(
    stream_generator: Generator[Message | message.MessageChunk | message.MessageStreamError | Chunk],
) -> Generator[str, Any, None]:
    try:
        for stream_message in stream_generator:
            match stream_message:
                case Message():
                    flat_messages = Thread.from_message(stream_message)

                    yield format_message(flat_messages)
                case APIInterface():
                    yield format_message(stream_message)
    except Exception as e:
        getLogger().exception("Error when streaming")
        raise e


def create_threads_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage) -> Blueprint:
    threads_blueprint = Blueprint("messages", __name__)

    @threads_blueprint.get("/")
    @anonymous_auth_protector()
    @pydantic_api(name="Get messages", tags=["v4", "threads"])
    def list_threads(request: GetThreadsRequest) -> GetThreadsResponse:
        authn()
        return get_threads(request, message_repository=MessageRepository(current_session))

    @threads_blueprint.get("/<thread_id>")
    @anonymous_auth_protector()
    @pydantic_api(name="Get message", tags=["v4", "threads"])
    def get_single_thread(thread_id: str) -> Thread:
        agent = authn()
        return get_thread(thread_id, user_id=agent.client, message_repository=MessageRepository(current_session))

    @threads_blueprint.post("/")
    @anonymous_auth_protector()
    @pydantic_api(name="Stream a prompt response", tags=["v4", "threads"])
    def create_message(
        create_message_request: CreateMessageRequest,
    ) -> ResponseReturnValue:
        try:
            stream_response = create_message_v4(
                create_message_request,
                dbc,
                storage_client=storage_client,
                message_repository=MessageRepository(current_session),
            )
            if isinstance(stream_response, Generator):
                return Response(stream_with_context(format_messages(stream_response)), mimetype="application/jsonl")
            return jsonify(stream_response)

        except ValidationError as e:
            return handle_validation_error(e)

    return threads_blueprint
