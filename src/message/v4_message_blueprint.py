from collections.abc import Generator
from typing import Any, cast

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask.typing import ResponseReturnValue
from flask_pydantic_api.api_wrapper import pydantic_api
from flask_pydantic_api.utils import UploadedFile
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.dao import label as old_label
from src.dao.engine_models.message import Message as SQLAMessage
from src.dao.engine_models.model_config import ModelType
from src.dao.flask_sqlalchemy_session import current_session
from src.dao.message.message_models import InferenceOpts, Message, Role
from src.dao.message.message_repository import MessageRepository
from src.error import handle_validation_error
from src.message.create_message_request import (
    CreateMessageRequest,
    CreateMessageRequestWithLists,
)
from src.message.create_message_service.endpoint import create_message_v4, format_message
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.map_text_snippet import text_snippet


def map_sqla_to_old(message: SQLAMessage) -> Message:
    # Map message.role to old Role enum; default to user if unknown
    try:
        mapped_role = Role(message.role)
    except Exception:
        mapped_role = Role.User

    # Map model_type to old enum when possible
    try:
        mapped_model_type = ModelType(message.model_type) if message.model_type is not None else None
    except Exception:
        mapped_model_type = None

    # Build InferenceOpts without re-validation
    mapped_opts = InferenceOpts.model_construct(**message.opts)

    # We don't currently expose logprobs from ORM messages in v4 stream
    mapped_logprobs = None

    # Map labels to old label dataclass if present
    mapped_labels: list[old_label.Label] = []
    if getattr(message, "labels", None):
        for lbl in cast(list, message.labels):
            mapped_labels.append(
                old_label.Label(
                    id=lbl.id,
                    message=lbl.message,
                    rating=old_label.Rating(lbl.rating),
                    creator=lbl.creator,
                    comment=lbl.comment,
                    created=lbl.created,
                    deleted=lbl.deleted,
                )
            )

    # Map children recursively if present
    mapped_children: list[Message] | None = None
    if getattr(message, "children", None):
        mapped_children = [map_sqla_to_old(child) for child in cast(list[SQLAMessage], message.children)]

    return Message(
        id=message.id,
        content=message.content,
        snippet=text_snippet(message.content),
        creator=message.creator,
        role=mapped_role,
        opts=mapped_opts,
        root=message.root,
        created=message.created,
        model_id=message.model_id,
        model_host=message.model_host,
        deleted=message.deleted,
        parent=message.parent,
        template=message.template,
        logprobs=mapped_logprobs,
        children=mapped_children,
        completion=message.completion,
        final=message.final,
        original=message.original,
        private=message.private,
        model_type=mapped_model_type,
        finish_reason=message.finish_reason,
        harmful=message.harmful,
        expiration_time=message.expiration_time,
        labels=mapped_labels,
        file_urls=message.file_urls,
        thinking=message.thinking,
    )


def format_messages(stream_generator: Generator) -> Generator[str, Any, None]:
    for message in stream_generator:
        match message:
            case SQLAMessage():
                # map Message to old messsage...
                yield format_message(map_sqla_to_old(message))
            case _:
                yield format_message(message)


def create_v4_message_blueprint(
    dbc: db.Client, storage_client: GoogleCloudStorage, session_maker: sessionmaker[Session]
) -> Blueprint:
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
                session_maker=session_maker,
                message_repository=MessageRepository(current_session),
            )
            if isinstance(stream_response, Generator):
                return Response(stream_with_context(format_messages(stream_response)), mimetype="application/jsonl")
            return jsonify(stream_response)

        except ValidationError as e:
            return handle_validation_error(e)

    return v4_message_blueprint
