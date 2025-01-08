from typing import Generator, cast

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask_pydantic_api.api_wrapper import pydantic_api
from flask_pydantic_api.utils import UploadedFile
from pydantic import ValidationError

from src import db
from src.dao.message import InferenceOpts
from src.message.create_message_request import (
    CreateMessageRequest,
    CreateMessageRequestWithLists,
)
from src.message.create_message_service import (
    CreateMessageRequest as CreateMessageRequestWithFullMessages,
)
from src.message.create_message_service import stream_new_message


def create_v4_message_blueprint(dbc: db.Client) -> Blueprint:
    v4_message_blueprint = Blueprint("message", __name__)

    @v4_message_blueprint.post("/stream")
    @pydantic_api(name="Stream a prompt response", tags=["v4", "message"])
    def create_message(create_message_request: CreateMessageRequest) -> Response:
        files = cast(list[UploadedFile], request.files.getlist("files"))

        stop_words = request.form.getlist("stop")

        try:
            # HACK: flask-pydantic-api has poor support for lists in form data
            # Making a separate class that handles lists works for now
            create_message_request_with_lists = CreateMessageRequestWithLists(
                **create_message_request.model_dump(), files=files, stop=stop_words
            )
        except ValidationError as e:
            response = jsonify({"errors": e.errors()})
            response.status_code = 400
            return response

        parent = (
            dbc.message.get(create_message_request_with_lists.parent)
            if create_message_request_with_lists.parent is not None
            else None
        )

        root = dbc.message.get(parent.root) if parent is not None else None

        mapped_request = CreateMessageRequestWithFullMessages(
            parent=parent,
            content=create_message_request_with_lists.content,
            role=create_message_request_with_lists.role,
            original=create_message_request_with_lists.original,
            private=create_message_request_with_lists.private,
            root=root,
            template=create_message_request_with_lists.template,
            model_id=create_message_request_with_lists.model_id,
            host=create_message_request_with_lists.host,
            opts=InferenceOpts.from_request(create_message_request.model_dump()),
            files=create_message_request_with_lists.files,
        )

        stream_response = stream_new_message(mapped_request, dbc)
        if isinstance(stream_response, Generator):
            return Response(
                stream_with_context(stream_response), mimetype="application/jsonl"
            )
        else:
            return jsonify(stream_response)

    return v4_message_blueprint
