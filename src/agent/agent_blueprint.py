from collections.abc import Generator
from typing import Annotated

from flask import Blueprint, Response, jsonify, stream_with_context
from pydantic import AfterValidator, Field, ValidationError, field_validator

from src import db
from src.agent.agent_config_service import get_agent_by_id
from src.api_interface import APIInterface
from src.auth.resource_protectors import anonymous_auth_protector
from src.dao.flask_sqlalchemy_session import current_session
from src.dao.message.message_models import Role
from src.dao.message.message_repository import MessageRepository
from src.error import handle_validation_error
from src.flask_pydantic_api.api_wrapper import pydantic_api
from src.message.create_message_request import captcha_token_required_if_captcha_enabled
from src.message.create_message_service.endpoint import (
    MessageType,
    ModelMessageStreamInput,
    stream_message_from_model,
)
from src.message.format_messages_output import format_messages
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.tools.mcp_service import find_mcp_config_by_id


class AgentChatRequest(APIInterface):
    agent_id: str
    parent: str | None = Field(default=None)
    content: str = Field(min_length=1)
    template: str | None = Field(default=None)
    bypass_safety_check: bool = Field(default=False)
    captcha_token: Annotated[str | None, AfterValidator(captcha_token_required_if_captcha_enabled)] = Field(
        default=None
    )

    @field_validator("content", mode="after")
    @classmethod
    def standardize_newlines(cls, value: str) -> str:
        return value.replace("\r\n", "\n")


def create_agents_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage) -> Blueprint:
    agents_blueprint = Blueprint(name="agents", import_name=__name__)

    @agents_blueprint.post("/chat")
    @anonymous_auth_protector()
    @pydantic_api(name="Stream a chat agent response", tags=["v4", "agents"])
    def stream_chat_agent_response(request: AgentChatRequest):
        agent = get_agent_by_id(request.agent_id)
        agent_mcp_servers = [find_mcp_config_by_id(mcp_server_id) for mcp_server_id in (agent.mcp_server_ids or [])]
        mcp_server_ids = {mcp_server.id for mcp_server in agent_mcp_servers if mcp_server is not None}

        stream_model_message_request = ModelMessageStreamInput(
            parent=request.parent,
            content=request.content,
            role=Role.User,
            original=None,
            private=False,
            template=request.template,
            model=agent.model_id,
            request_type=MessageType.AGENT,
            mcp_server_ids=mcp_server_ids,
            enable_tool_calling=True,
        )

        try:
            stream_response = stream_message_from_model(
                stream_model_message_request,
                dbc,
                storage_client=storage_client,
                message_repository=MessageRepository(current_session),
            )
            if isinstance(stream_response, Generator):
                return Response(stream_with_context(format_messages(stream_response)), mimetype="application/jsonl")
            return jsonify(stream_response)

        except ValidationError as e:
            return handle_validation_error(e)

    return agents_blueprint
