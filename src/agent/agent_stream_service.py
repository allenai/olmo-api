from typing import Annotated

from pydantic import AfterValidator, Field, field_validator

from pydantic_ai import Agent
from src import db
from src.agent.agent_config_service import get_agent_by_id
from src.api_interface import APIInterface
from src.auth.auth_service import authn
from src.config.get_models import get_model_by_id, get_pydantic_model_by_id
from src.dao.flask_sqlalchemy_session import current_session
from src.dao.message.message_models import Role
from src.dao.message.message_repository import MessageRepository
from src.message.create_message_request import captcha_token_required_if_captcha_enabled
from src.message.create_message_service.endpoint import (
    MessageType,
    ModelMessageStreamInput,
    stream_message_from_model,
    validate_chat_stream_request,
)
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.pydantic_ai.playground_ui_adapter import PlaygroundUIAdapter
from src.pydantic_inference.pydantic_ai_helpers import pydantic_settings_map


class AgentChatRequest(APIInterface):
    agent_id: str
    parent: str | None = Field(default=None)
    content: str = Field(min_length=1)
    template: str | None = Field(default=None)
    bypass_safety_check: bool = Field(default=False)
    captcha_token: Annotated[str | None, AfterValidator(captcha_token_required_if_captcha_enabled)] = Field(
        default=None
    )
    max_steps: int | None = Field(default=None)

    @field_validator("content", mode="after")
    @classmethod
    def standardize_newlines(cls, value: str) -> str:
        return value.replace("\r\n", "\n")


def stream_agent_chat(request: AgentChatRequest, dbc: db.Client, storage_client: GoogleCloudStorage):
    agent = get_agent_by_id(request.agent_id)

    stream_model_message_request = ModelMessageStreamInput(
        parent=request.parent,
        content=request.content,
        role=Role.User,
        original=None,
        private=False,
        template=request.template,
        model=agent.model_id,
        request_type=MessageType.AGENT,
        enable_tool_calling=True,
        max_steps=request.max_steps,
    )

    model = get_model_by_id(agent.model_id)
    client_auth = authn()
    mapped_request, start_time_ns, safety_check_elapsed_time, is_message_harmful = validate_chat_stream_request(
        request=stream_model_message_request,
        message_repository=MessageRepository(current_session),
        model=model,
        client_auth=client_auth,
        agent_id=agent.id,
    )

    pydantic_model = get_pydantic_model_by_id(agent.id)

    pydantic_agent = Agent(
        model=pydantic_model,
        toolsets=agent.toolsets,
        model_settings=pydantic_settings_map(
            opts=mapped_request.opts, model_config=model, extra_body=agent.extra_inference_opts
        ),
    )

    stream_adapter = PlaygroundUIAdapter()
    return stream_message_from_model(
        stream_model_message_request,
        dbc,
        storage_client=storage_client,
        message_repository=MessageRepository(current_session),
    )
