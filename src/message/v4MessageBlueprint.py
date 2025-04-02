from collections.abc import Generator
from typing import cast

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask.typing import ResponseReturnValue
from flask_pydantic_api.api_wrapper import pydantic_api
from flask_pydantic_api.utils import UploadedFile
from pydantic import ValidationError

from src import db
from src.error import handle
from src.message.create_message_request import (
    CreateMessageRequestV4,
    CreateMessageRequestV4WithLists,
)
from src.message.create_message_service import (
    create_message_v4,
)
from src.message.GoogleCloudStorage import GoogleCloudStorage


def create_v4_message_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage) -> Blueprint:
    v4_message_blueprint = Blueprint("message", __name__)

    @v4_message_blueprint.post("/stream")
    @pydantic_api(name="Stream a prompt response", tags=["v4", "message"])
    def create_message(
        create_message_request: CreateMessageRequestV4,
    ) -> ResponseReturnValue:
        request_files = request.files.getlist("files")
        # Defaulting to an empty list can cause problems with Modal
        # This isn't happening from the UI but it is happening through e2e tests, so better safe than sorry!
        files = cast(list[UploadedFile], request_files) if len(request_files) > 0 else None

        stop_words = request.form.getlist("stop")

        try:
            # HACK: flask-pydantic-api has poor support for lists in form data
            # Making a separate class that handles lists works for now
            create_message_request_with_lists = CreateMessageRequestV4WithLists(
                **create_message_request.model_dump(), files=files, stop=stop_words
            )

            stream_response = create_message_v4(create_message_request_with_lists, dbc, storage_client=storage_client)
            if isinstance(stream_response, Generator):
                return Response(stream_with_context(stream_response), mimetype="application/jsonl")
            return jsonify(stream_response)

        except Exception as e:
            return handle(e)

    return v4_message_blueprint
