from datetime import UTC, datetime, timedelta

from werkzeug import exceptions

from src import obj
from src.auth.token import Token
from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig
from src.dao.engine_models.tool_call import ToolCall
from src.dao.message.message_models import Role
from src.dao.message.message_repository import BaseMessageRepository
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
)


def get_expiration_time(agent: Token):
    # We currently want anonymous users' messages to expire after 1 days
    return datetime.now(UTC) + timedelta(days=1) if agent.is_anonymous_user else None


def setup_msg_thread(
    message_repository: BaseMessageRepository,
    model: ModelConfig,
    request: CreateMessageRequestWithFullMessages,
    agent: Token,
    is_msg_harmful: bool | None = None,
) -> list[Message]:
    system_msg = None
    message_chain: list[Message] = []

    msg_id = obj.NewID("msg")
    message_expiration_time = get_expiration_time(agent)

    if request.parent is None and model.default_system_prompt is not None:
        system_msg = Message(
            id=msg_id,
            content=model.default_system_prompt,
            creator=agent.client,
            role=Role.System,
            opts=request.opts.model_dump(),
            model_id=model.id,
            model_host=model.host,
            root=msg_id,
            parent=None,
            template=request.template,
            final=False,
            original=request.original,
            private=request.private,
            harmful=is_msg_harmful,
            expiration_time=message_expiration_time,
        )

        message_repository.add(system_msg)

    if request.parent:
        parent = message_repository.get_message_by_id(request.parent.id)
        if parent is None:
            raise exceptions.NotFound
        message_chain.append(parent)

    if request.root is not None:
        messages = message_repository.get_messages_by_root(request.root.id, agent.client) or []
        msgs: dict[str, Message] = {}
        for message in messages:
            msgs[message.id] = message

        while message_chain[-1].parent is not None:
            message_chain.append(msgs[message_chain[-1].parent])

    if system_msg is not None:
        message_chain.append(system_msg)

    message_chain.reverse()

    return message_chain


def create_user_message(
    message_repository: BaseMessageRepository,
    request: CreateMessageRequestWithFullMessages,
    parent: Message | None,
    agent: Token,
    model: ModelConfig,
    is_msg_harmful: bool | None = None,
):
    message_expiration_time = get_expiration_time(agent)

    msg_id = obj.NewID("msg")
    message = Message(
        id=msg_id,
        content=request.content,
        creator=agent.client,
        role=request.role,
        opts=request.opts.model_dump(),
        model_id=model.id,
        model_host=model.host,
        root=parent.root if parent is not None else msg_id,
        parent=parent.id if parent is not None else None,
        template=request.template,
        final=False,
        original=request.original,
        private=request.private,
        harmful=is_msg_harmful,
        expiration_time=message_expiration_time,
    )
    return message_repository.add(message)


def create_tool_response_message(
    message_repository: BaseMessageRepository, parent_message: Message, content: str, source_tool: ToolCall
):
    message = Message(
        content=content,
        creator=parent_message.creator,
        role=Role.ToolResponse,
        opts=parent_message.opts,
        model_id=parent_message.model_id,
        model_host=parent_message.model_host,
        model_type=parent_message.model_type,
        root=parent_message.root,
        parent=parent_message.id,
        template=None,
        final=True,
        original=None,
        private=parent_message.private,
        harmful=False,
        expiration_time=parent_message.expiration_time,
        tool_calls=[source_tool],
    )
    return message_repository.add(message)


def create_assistant_message(
    message_repository: BaseMessageRepository,
    content: str,
    request: CreateMessageRequestWithFullMessages,
    model: ModelConfig,
    parent_message_id: str,
    root_message_id: str,
    agent: Token,
):
    message_expiration_time = get_expiration_time(agent)

    message = Message(
        content=content,
        creator=agent.client,
        role=Role.Assistant,
        opts=request.opts.model_dump(),
        model_id=request.model,
        model_host=request.host,
        root=root_message_id,
        parent=parent_message_id,
        final=False,
        private=request.private,
        model_type=model.model_type,
        expiration_time=message_expiration_time,
    )
    return message_repository.add(message)
