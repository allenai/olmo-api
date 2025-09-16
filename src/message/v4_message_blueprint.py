from collections.abc import Generator
from typing import Any

from flask import Blueprint, Response, jsonify, stream_with_context
from flask.typing import ResponseReturnValue
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.dao.engine_models.message import Message as SQLAMessage
from src.dao.flask_sqlalchemy_session import current_session
from src.dao.message.message_repository import MessageRepository, map_sqla_to_old
from src.error import handle_validation_error
from src.flask_pydantic_api.api_wrapper import pydantic_api
from src.message.create_message_request import (
    CreateMessageRequest,
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

    return v4_message_blueprint
