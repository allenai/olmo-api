from collections.abc import Generator
from logging import getLogger
from typing import Any, cast

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask.typing import ResponseReturnValue
from flask_pydantic_api.api_wrapper import pydantic_api
from flask_pydantic_api.utils import UploadedFile
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.api_interface import APIInterface
from src.dao import message
from src.dao.flask_sqlalchemy_session import current_session
from src.dao.message_respository import MessageRepository
from src.error import handle_validation_error
from src.message.create_message_request import (
    CreateMessageRequest,
    CreateMessageRequestWithLists,
)
from src.message.create_message_service.endpoint import create_message_v4, format_message
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.thread.get_thread_service import get_thread
from src.thread.get_threads_service import GetThreadsRequest, GetThreadsResponse, get_threads
from src.thread.thread_models import Thread


def format_messages(
    stream_generator: Generator[message.Message | message.MessageChunk | message.MessageStreamError, Any, None],
) -> Generator[str, Any, None]:
    try:
        for stream_message in stream_generator:
            match stream_message:
                case message.Message():
                    flat_messages = Thread.from_message(stream_message)

                    yield format_message(flat_messages)
                case APIInterface():
                    yield format_message(stream_message)
    except Exception as e:
        getLogger().exception("Error when streaming")
        raise e


def create_threads_blueprint(
    dbc: db.Client, session_maker: sessionmaker[Session], storage_client: GoogleCloudStorage
) -> Blueprint:
    threads_blueprint = Blueprint("messages", __name__)

    @threads_blueprint.get("/")
    @pydantic_api(name="Get messages", tags=["v4", "threads"])
    def list_threads(request: GetThreadsRequest) -> GetThreadsResponse:
        return get_threads(dbc, request)

    @threads_blueprint.get("/<thread_id>")
    @pydantic_api(name="Get message", tags=["v4", "threads"])
    def get_single_thread(thread_id: str) -> Thread:
        return get_thread(thread_id, dbc=dbc, message_repository=MessageRepository(current_session))

    @threads_blueprint.post("/")
    @pydantic_api(name="Stream a prompt response", tags=["v4", "threads"])
    def create_message(
        create_message_request: CreateMessageRequest,
    ) -> ResponseReturnValue:
        request_files = request.files.getlist("files")
        # Defaulting to an empty list can cause problems with Modal
        # This isn't happening from the UI but it is happening through e2e tests, so better safe than sorry!
        files = cast(list[UploadedFile], request_files) if len(request_files) > 0 else None

        stop_words = request.form.getlist("stop")

        try:
            # HACK: flask-pydantic-api has poor support for lists in form data
            # Making a separate class that handles lists works for now
            create_message_request_with_lists = CreateMessageRequestWithLists(
                **create_message_request.model_dump(), files=files, stop=stop_words
            )

            stream_response = create_message_v4(
                create_message_request_with_lists, dbc, storage_client=storage_client, session_maker=session_maker
            )
            if isinstance(stream_response, Generator):
                return Response(stream_with_context(format_messages(stream_response)), mimetype="application/jsonl")
            return jsonify(stream_response)

        except ValidationError as e:
            return handle_validation_error(e)

    return threads_blueprint
