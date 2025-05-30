from collections.abc import Generator
from dataclasses import asdict
from datetime import datetime
from typing import Any, cast

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask.typing import ResponseReturnValue
from flask_pydantic_api.api_wrapper import pydantic_api
from flask_pydantic_api.utils import UploadedFile
from pydantic import AwareDatetime, Field, ValidationError, computed_field
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.api_interface import APIInterface
from src.dao import message
from src.dao.engine_models.model_config import ModelType
from src.dao.label import Rating
from src.dao.message import InferenceOpts, Role
from src.error import handle_validation_error
from src.inference.InferenceEngine import FinishReason
from src.message.create_message_request import (
    CreateMessageRequest,
    CreateMessageRequestWithLists,
)
from src.message.create_message_service import (
    create_message_v4,
    format_message,
)
from src.message.GoogleCloudStorage import GoogleCloudStorage


class LabelResponse(APIInterface):
    id: str
    message: str
    rating: Rating
    creator: str
    comment: str | None = Field(default=None)
    created: AwareDatetime
    deleted: AwareDatetime | None = Field(default=None)


class InferenceOptionsResponse(InferenceOpts, APIInterface): ...


class LogProbResponse(APIInterface):
    token_id: int
    text: str
    logprob: float


class FlatMessage(APIInterface):
    id: str
    content: str
    snippet: str
    creator: str
    role: Role
    opts: InferenceOptionsResponse
    root: str
    created: AwareDatetime
    model_id: str
    model_host: str
    deleted: AwareDatetime | None = Field(default=None)
    parent: str | None = Field(default=None)
    template: str | None = Field(default=None)
    children: list[str] | None = Field(default=None)
    completion: str | None = Field(default=None)
    final: bool = Field(default=False)
    original: str | None = Field(default=None)
    private: bool = Field(default=False)
    model_type: ModelType | None = None
    finish_reason: FinishReason | None = None
    harmful: bool | None = None
    expiration_time: AwareDatetime | None = Field(default=None)
    labels: list[LabelResponse] = Field(default_factory=list)
    file_urls: list[str] | None = Field(default=None)

    @computed_field  # type:ignore
    @property
    def is_limit_reached(self) -> bool:
        return self.finish_reason == FinishReason.Length

    @computed_field  # type:ignore
    @property
    def is_older_than_30_days(self) -> bool:
        time_since_creation = datetime.now(tz=self.created.tzinfo) - self.created
        return time_since_creation.days > 30  # noqa: PLR2004

    @staticmethod
    def from_message(message: message.Message) -> list["FlatMessage"]:
        messages = [asdict(message_in_list) for message_in_list in message.flatten()]
        for message_to_change in messages:
            children = message_to_change.get("children", [])
            if children is not None:
                message_to_change["children"] = [child.get("id") for child in children]

        return [FlatMessage.model_validate(mapped_message) for mapped_message in messages]


class MessageChunkResponse(APIInterface):
    message: str
    content: str


def format_messages(
    stream_generator: Generator[message.Message | message.MessageChunk | message.MessageStreamError, Any, None],
) -> Generator[str, Any, None]:
    for stream_message in stream_generator:
        match stream_message:
            case message.Message():
                flat_messages = FlatMessage.from_message(stream_message)

                yield format_message(flat_messages)
            case APIInterface():
                yield format_message(stream_message)


def create_v5_message_blueprint(
    dbc: db.Client, storage_client: GoogleCloudStorage, session_maker: sessionmaker[Session]
) -> Blueprint:
    v5_message_blueprint = Blueprint("message", __name__)

    @v5_message_blueprint.post("/stream")
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
                create_message_request_with_lists, dbc, storage_client=storage_client, session_maker=session_maker
            )
            if isinstance(stream_response, Generator):
                return Response(stream_with_context(format_messages(stream_response)), mimetype="application/jsonl")
            return jsonify(stream_response)

        except ValidationError as e:
            return handle_validation_error(e)

    return v5_message_blueprint
