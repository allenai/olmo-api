from datetime import UTC, datetime, timedelta

from werkzeug import exceptions

from src import obj
from src.auth.token import Token
from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition, ToolSource
from src.dao.message.message_models import Role
from src.dao.message.message_repository import BaseMessageRepository
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
)
from src.tools.tools_service import get_available_tools


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


def map_tools_for_user_message(
    request: CreateMessageRequestWithFullMessages,
    parent: Message | None,
    model: ModelConfig,
) -> list[ToolDefinition]:
    is_new_thread = request.parent is None

    # We can't currently change tools in the middle of a thread. If we're adding to a thread, use the parent's tools
    if not is_new_thread:
        return parent.tool_definitions or [] if parent is not None else []

    if request.enable_tool_calling is False:
        return []

    user_defined_tools: list[ToolDefinition] = [
        ToolDefinition(
            name=tool_def.name,
            description=tool_def.description,
            parameters=tool_def.parameters.model_dump(),
            tool_source=ToolSource.USER_DEFINED,
        )
        for tool_def in request.create_tool_definitions or []
    ]

    selected_tools = (
        [tool for tool in get_available_tools(model) if tool.name in request.selected_tools]
        if request.selected_tools is not None
        else []
    )

    tool_list: list[ToolDefinition] = selected_tools + user_defined_tools

    return tool_list


def create_user_message(
    message_repository: BaseMessageRepository,
    request: CreateMessageRequestWithFullMessages,
    parent: Message | None,
    agent: Token,
    model: ModelConfig,
    *,
    is_msg_harmful: bool | None = None,
):
    tool_list: list[ToolDefinition] = map_tools_for_user_message(request, parent, model)

    tool_names = [obj.name for obj in tool_list]

    if len(tool_names) != len(set(tool_names)):
        msg = f"tool name conflict detected for name in list {tool_names}"
        raise RuntimeError(msg)

    message_expiration_time = get_expiration_time(agent)

    msg_id = obj.NewID("msg")
    message = Message(
        id=msg_id,
        content=request.content,
        creator=agent.client,
        role=Role.User,
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
        tool_definitions=tool_list,
        extra_parameters=request.extra_parameters,
    )
    return message_repository.add(message)


def create_tool_response_message(
    message_repository: BaseMessageRepository,
    parent: Message,
    content: str,
    source_tool: ToolCall,
    creator: str,
):
    message = Message(
        content=content,
        role=Role.ToolResponse,
        opts=parent.opts,
        model_id=parent.model_id,
        model_host=parent.model_host,
        model_type=parent.model_type,
        root=parent.root,
        parent=parent.id,
        template=None,
        final=True,
        original=None,
        private=parent.private,
        harmful=False,
        expiration_time=parent.expiration_time,
        creator=creator,
        tool_calls=[clone_tool_call(source_tool)],
        tool_definitions=parent.tool_definitions,
    )

    return message_repository.add(message)


def create_assistant_message(
    message_repository: BaseMessageRepository,
    content: str,
    parent: Message,
    model: ModelConfig,
    agent: Token,
):
    message_expiration_time = get_expiration_time(agent)

    message = Message(
        content=content,
        creator=agent.client,
        role=Role.Assistant,
        opts=parent.opts,
        model_id=model.id,
        model_host=model.host,
        root=parent.root,
        parent=parent.id,
        final=False,
        private=parent.private,
        model_type=model.model_type,
        expiration_time=message_expiration_time,
        tool_definitions=parent.tool_definitions,
    )
    return message_repository.add(message)


def clone_tool_call(source_tool: ToolCall):
    return ToolCall(
        tool_call_id=source_tool.tool_call_id,
        args=source_tool.args,
        tool_name=source_tool.tool_name,
        message_id="",
        tool_source=source_tool.tool_source,
    )
