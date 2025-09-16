from collections.abc import Generator
from typing import Any, cast

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask.typing import ResponseReturnValue
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.dao.engine_models.message import Message as SQLAMessage
from src.dao.flask_sqlalchemy_session import current_session
from src.dao.message.message_repository import MessageRepository, map_sqla_to_old
from src.error import handle_validation_error
from src.flask_pydantic_api.api_wrapper import pydantic_api
from src.flask_pydantic_api.utils import UploadedFile
from src.message.create_message_request import (
    CreateMessageRequest,
    CreateMessageRequestWithLists,
)
from src.message.create_message_service.endpoint import create_message_v4, format_message
from src.message.GoogleCloudStorage import GoogleCloudStorage


def format_messages(stream_generator: Generator) -> Generator[str, Any, None]:
    for message in stream_generator:
        match message:
            case SQLAMessage():
                # map Message to old messsage...
                yield format_message(map_sqla_to_old(message))
            case _:
                yield format_message(message)


def create_v4_message_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage) -> Blueprint:
    v4_message_blueprint = Blueprint("message", __name__)

    @v4_message_blueprint.post("/stream")
    @pydantic_api(name="Stream a prompt response", tags=["v4", "message"])
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
                create_message_request_with_lists,
                dbc,
                storage_client=storage_client,
                message_repository=MessageRepository(current_session),
            )
            if isinstance(stream_response, Generator):
                return Response(stream_with_context(format_messages(stream_response)), mimetype="application/jsonl")
            return jsonify(stream_response)

        except ValidationError as e:
            return handle_validation_error(e)

    return v4_message_blueprint
