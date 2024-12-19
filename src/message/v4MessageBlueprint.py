import logging
from typing import Optional

from flask import Blueprint, Response, jsonify, request
from pydantic import ConfigDict, Field
from werkzeug.datastructures import FileStorage

from src import db
from src.api_interface import APIInterface
from src.dao.message import Role


class CreateMessageRequest(APIInterface):
    parent: Optional[str] = Field(default=None)
    max_tokens: int
    temperature: float
    n: int
    top_p: float
    logprobs: Optional[int] = Field(default=None)
    stop: Optional[list[str]] = Field(default=None)
    content: str = Field(min_length=1)
    role: Role
    original: str
    private: bool
    root: Optional[str] = Field(default=None)
    template: str
    model_id: str
    host: str
    image: Optional[FileStorage] = Field(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)


def create_v4_message_blueprint(dbc: db.Client) -> Blueprint:
    v4_message_blueprint = Blueprint("message", __name__)

    # @v4_message_blueprint.post("/stream")
    def create_message() -> Response:
        logger = logging.getLogger()
        logger.info(str(request.form.to_dict()))
        mapped_request = CreateMessageRequest(**request.form, **request.files)

        return jsonify(mapped_request)

    v4_message_blueprint.post("/stream")(create_message)

    return v4_message_blueprint


class v4MessageBlueprint(Blueprint):
    def __init__(self, dbc: db.Client):
        super().__init__(name="v4_message", import_name=__name__)

        self.dbc = dbc
