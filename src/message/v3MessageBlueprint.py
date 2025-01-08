from typing import Generator

from flask import Blueprint, Response, jsonify
from flask_pydantic_api.api_wrapper import pydantic_api

from src import db
from src.message.create_message_request import CreateMessageRequestWithFullMessages
from src.message.create_message_service import create_message as create_message_service
from src.message.message_service import delete_message as delete_message_service
from src.message.message_service import get_message


def create_v3_message_blueprint(dbc: db.Client) -> Blueprint:
    v3_message_blueprint = Blueprint(name="message", import_name=__name__)

    @v3_message_blueprint.post("/")
    @v3_message_blueprint.post("/stream")
    @pydantic_api(name="Stream a prompt response", tags=["v3", "message"])
    def create_message(
        create_message_request: CreateMessageRequestWithFullMessages,
    ) -> Response:
        response = create_message_service(create_message_request, dbc)

        if isinstance(response, Generator):
            return Response(response, mimetype="application/jsonl")
        else:
            return jsonify(response)

    @v3_message_blueprint.get("/<string:id>")
    def message(id: str):
        message = get_message(id=id, dbc=dbc)
        return jsonify(message)

    @v3_message_blueprint.delete("/<string:id>")
    def delete_message(id: str):
        deleted_message = delete_message_service(id=id, dbc=dbc)
        return jsonify(deleted_message)

    return v3_message_blueprint
