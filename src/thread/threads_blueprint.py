from collections.abc import Generator

from flask import Blueprint, Response, jsonify, stream_with_context
from flask.typing import ResponseReturnValue
from pydantic import ValidationError

from src import db
from src.auth.auth_service import authn
from src.auth.resource_protectors import anonymous_auth_protector
from src.dao.flask_sqlalchemy_session import current_session
from src.dao.message.message_repository import MessageRepository
from src.error import handle_validation_error
from src.flask_pydantic_api.api_wrapper import pydantic_api
from src.message.create_message_request import CreateMessageRequest
from src.message.create_message_service.endpoint import (
    MessageType,
    ModelMessageStreamInput,
    stream_message_from_model,
)
from src.message.format_messages_output import format_messages
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.thread.get_thread_service import get_thread
from src.thread.get_threads_service import GetThreadsRequest, GetThreadsResponse, get_threads
from src.thread.thread_models import Thread


def create_threads_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage) -> Blueprint:
    threads_blueprint = Blueprint("messages", __name__)

    @threads_blueprint.get("/")
    @anonymous_auth_protector()
    @pydantic_api(name="Get messages", tags=["v4", "threads"], get_request_model_from_query_string=True)
    def list_threads(request: GetThreadsRequest) -> GetThreadsResponse:
        authn()
        return get_threads(request, message_repository=MessageRepository(current_session))

    @threads_blueprint.get("/<thread_id>")
    @anonymous_auth_protector()
    @pydantic_api(name="Get message", tags=["v4", "threads"])
    def get_single_thread(thread_id: str) -> Thread:
        agent = authn()
        return get_thread(thread_id, user_id=agent.client, message_repository=MessageRepository(current_session))

    @threads_blueprint.post("/")
    @anonymous_auth_protector()
    @pydantic_api(name="Stream a prompt response", tags=["v4", "threads"])
    def create_message(
        create_message_request: CreateMessageRequest,
    ) -> ResponseReturnValue:
        model_message_stream_input = ModelMessageStreamInput(
            **create_message_request.model_dump(exclude={"host", "n", "logprobs"}, by_alias=False),
            request_type=MessageType.MODEL,
        )

        model_message_stream_input.input_parts = create_message_request.input_parts

        try:
            stream_response = stream_message_from_model(
                model_message_stream_input,
                dbc,
                storage_client=storage_client,
                message_repository=MessageRepository(current_session),
            )
            if isinstance(stream_response, Generator):
                return Response(stream_with_context(format_messages(stream_response)), mimetype="application/jsonl")
            return jsonify(stream_response)

        except ValidationError as e:
            return handle_validation_error(e)

    return threads_blueprint
