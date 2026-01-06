from collections.abc import Generator

from flask import Blueprint, Response, jsonify, stream_with_context
from pydantic import ValidationError

from src import db
from src.agent.agent_stream_service import AgentChatRequest, stream_agent_chat
from src.auth.resource_protectors import anonymous_auth_protector
from src.error import handle_validation_error
from src.flask_pydantic_api.api_wrapper import pydantic_api
from src.message.format_messages_output import format_messages
from src.message.GoogleCloudStorage import GoogleCloudStorage


def create_agents_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage) -> Blueprint:
    agents_blueprint = Blueprint(name="agents", import_name=__name__)

    @agents_blueprint.post("/chat")
    @anonymous_auth_protector()
    @pydantic_api(name="Stream a chat agent response", tags=["v4", "agents"])
    def stream_chat_agent_response(request: AgentChatRequest):
        try:
            stream_response = stream_agent_chat(request=request, dbc=dbc, storage_client=storage_client)
            if isinstance(stream_response, Generator):
                return Response(stream_with_context(format_messages(stream_response)), mimetype="application/jsonl")
            return jsonify(stream_response)

        except ValidationError as e:
            return handle_validation_error(e)

    return agents_blueprint
