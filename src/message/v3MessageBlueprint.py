from collections.abc import Generator

from flask import Blueprint, Response, jsonify
from flask.typing import ResponseReturnValue
from flask_pydantic_api.api_wrapper import pydantic_api
from pydantic import ValidationError

from src import db
from src.error import handle_validation_error
from src.message.create_message_request import CreateMessageRequestV3
from src.message.create_message_service import (
    create_message_v3 as create_message_service,
)
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.message_service import delete_message as delete_message_service
from src.message.message_service import get_message


def create_v3_message_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage) -> Blueprint:
    v3_message_blueprint = Blueprint(name="message", import_name=__name__)

    @v3_message_blueprint.post("/")
    @v3_message_blueprint.post("/stream")
    @pydantic_api(name="Stream a prompt response", tags=["v3", "message"])
    def create_message(
        create_message_request: CreateMessageRequestV3,
    ) -> ResponseReturnValue:
        try:
            response = create_message_service(create_message_request, dbc, storage_client=storage_client)

            if isinstance(response, Generator):
                return Response(response, mimetype="application/jsonl")
            return jsonify(response)

        except ValidationError as e:
            return handle_validation_error(e)

    @v3_message_blueprint.get("/<string:id>")
    def message(id: str):
        message = get_message(id=id, dbc=dbc)
        return jsonify(message)

    @v3_message_blueprint.delete("/<string:id>")
    def delete_message(id: str):
        deleted_message = delete_message_service(id=id, dbc=dbc, storage_client=storage_client)
        return jsonify(deleted_message)

    return v3_message_blueprint
