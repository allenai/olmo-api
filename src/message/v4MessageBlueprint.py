from typing import Optional, Self, cast

from flask import Blueprint, Response, jsonify, request
from flask_pydantic_api.api_wrapper import pydantic_api
from flask_pydantic_api.utils import UploadedFile
from pydantic import (
    ConfigDict,
    Field,
    SkipValidation,
    field_serializer,
    model_validator,
)

from src import db
from src.api_interface import APIInterface
from src.dao.message import Role


class CreateMessageRequest(APIInterface):
    # TODO: Validate that the parent role is different from this role and that it exists
    parent: Optional[str] = Field(default=None)
    max_tokens: int
    temperature: float
    n: Optional[int] = Field(default=1, ge=1, le=50, multiple_of=1)
    top_p: Optional[float] = Field(default=1.0, ge=0.01, le=1.0, multiple_of=0.01)
    logprobs: Optional[int] = Field(default=None, ge=0, le=10, multiple_of=1)
    # Mapping for this is handled in the controller
    stop: SkipValidation[Optional[list[str]]] = Field(default=None)
    content: str = Field(min_length=1)
    role: Role
    original: Optional[str] = Field(default=None)
    private: bool
    root: Optional[str] = Field(default=None)
    template: Optional[str] = Field(default=None)
    model_id: str
    host: str

    # Mapping for this is handled in the controller
    files: SkipValidation[Optional[list[UploadedFile]]] = Field(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def check_original_and_parent_are_different(self) -> Self:
        if self.original is not None and self.parent == self.original:
            raise ValueError("The original message cannot also be the parent")

        return self

    @model_validator(mode="after")
    def check_assistant_message_has_a_parent(self) -> Self:
        if self.role is Role.Assistant and self.parent is None:
            raise ValueError("Assistant messages must have a parent")

        return self

    # TODO: Remove this when we have real output
    @field_serializer("files")
    def serialize_files(self, files: Optional[list[UploadedFile]]):
        if files is not None:
            return [file.filename for file in files]
        else:
            return None


def create_v4_message_blueprint(dbc: db.Client) -> Blueprint:
    v4_message_blueprint = Blueprint("message", __name__)

    @v4_message_blueprint.post("/stream")
    @pydantic_api(name="Stream a prompt response", tags=["v4", "message"])
    def create_message(create_message_request: CreateMessageRequest) -> Response:
        # HACK: flask-pydantic-api has poor support for lists in form data, this gets around that for files
        create_message_request.files = cast(
            list[UploadedFile], request.files.getlist("files")
        )

        # HACK: flask-pydantic-api has poor support for lists in form data, this gets around that for stop words
        create_message_request.stop = request.form.getlist("stop")

        return jsonify(create_message_request.model_dump())

    return v4_message_blueprint


class v4MessageBlueprint(Blueprint):
    def __init__(self, dbc: db.Client):
        super().__init__(name="v4_message", import_name=__name__)

        self.dbc = dbc
