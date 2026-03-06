import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import TypeAlias, assert_never

from pydantic_ai import (
    BaseToolCallPart,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolReturnPart,
)

from api.thread.chat.chat_types import ChatStreamOutput
from api.thread.chat.mapping.pydantic_ai_mapping import MessageAndFiles
from core.message.role import Role
from core.object_id import ID
from core.tools.tool_source import ToolSource
from db.models.inference_opts import InferenceOpts
from db.models.message import Message
from db.models.model_config import ModelConfig
from db.models.tool_call import ToolCall
from db.models.tool_definitions import ToolDefinition

__all__ = ["Event", "InputMessage", "RunInput"]


InputMessage: TypeAlias = MessageAndFiles
Event: TypeAlias = ChatStreamOutput


@dataclass
class RunInput:
    all_messages: Sequence[MessageAndFiles]
    new_messages: Sequence[MessageAndFiles]
    parent_message_id: ID
    root_message_id: ID
    creator: str
    inference_opts: InferenceOpts
    model: ModelConfig
    user_tool_names: Sequence[str]
    tool_definitions: list[ToolDefinition] | None
    handle_final_messages: Callable[[Sequence[Message]], Awaitable[Message]]
    is_new_thread: bool


def create_message_from_run_input(
    *,
    run_input: RunInput,
    id: ID,
    content: str,
    role: Role,
    parent: ID,
    tool_calls: list[ToolCall] | None,
    thinking: str | None,
):
    return Message(
        id=id,
        content=content,
        role=role,
        creator=run_input.creator,
        opts=run_input.inference_opts,
        root=run_input.root_message_id,
        parent=parent,
        model_id=run_input.model.id,
        model_host=run_input.model.host,
        model_type=run_input.model.model_type,
        tool_calls=tool_calls or [],
        tool_definitions=run_input.tool_definitions or [],
        thinking=thinking,
    )


def map_tool_return_part_to_message(
    part: ToolReturnPart, message_id: ID, parent_message_id: ID, run_input: RunInput
) -> Message:
    tool_calls = [
        ToolCall(
            tool_call_id=part.tool_call_id,
            tool_name=part.tool_name,
            tool_source=ToolSource.MCP,  # TODO: Figure out how to differentiate between internal and MCP tools
            args=part.model_response_object(),
            message_id=message_id,
        )
    ]

    message = create_message_from_run_input(
        run_input=run_input,
        id=message_id,
        content=part.model_response_str(),
        role=Role.ToolResponse,
        parent=parent_message_id,
        tool_calls=tool_calls,
        thinking=None,
    )

    return message


def tool_source_from_name(tool_name: str, user_tool_names: Sequence[str]) -> ToolSource:
    # TODO: Figure out how to tell if a tool is internal
    return ToolSource.USER_DEFINED if tool_name in user_tool_names else ToolSource.MCP


def map_tool_call_part_to_tool_call(part: BaseToolCallPart, message_id: ID, user_tool_names: Sequence[str]) -> ToolCall:
    tool_source = tool_source_from_name(tool_name=part.tool_name, user_tool_names=user_tool_names)
    return ToolCall(
        tool_call_id=part.tool_call_id,
        tool_name=part.tool_name,
        tool_source=tool_source,
        message_id=message_id,
        args=part.args if isinstance(part.args, dict) else json.loads(part.args or "null"),
    )


def map_response_pydantic_messages_to_messages(
    messages: Sequence[ModelMessage], message_ids: Sequence[ID], run_input: RunInput
) -> list[Message]:
    parent_message_id = run_input.parent_message_id

    mapped_messages: list[Message] = []
    for i, message in enumerate(messages):
        message_id = message_ids[i]
        match message:
            case ModelRequest():
                for request_part in message.parts:
                    match request_part:
                        case ToolReturnPart():
                            tool_return_message = map_tool_return_part_to_message(
                                request_part,
                                message_id=message_id,
                                parent_message_id=parent_message_id,
                                run_input=run_input,
                            )
                            mapped_messages.append(tool_return_message)
                            parent_message_id = tool_return_message.id
                        case _:
                            # We don't expect to have any other parts in the the messages the Pydantic-AI Agent made
                            pass

            case ModelResponse():
                message_content = ""
                message_thinking: str | None = None
                message_tool_calls: list[ToolCall] = []

                for response_part in message.parts:
                    match response_part:
                        case TextPart():
                            message_content += response_part.content
                        case BaseToolCallPart():
                            tool_call = map_tool_call_part_to_tool_call(
                                response_part, message_id, run_input.user_tool_names
                            )
                            message_tool_calls.append(tool_call)
                        case ThinkingPart():
                            if message_thinking is None:
                                message_thinking = response_part.content
                            else:
                                message_thinking += response_part.content
                        case _:
                            # We don't expect to have any other parts in the the messages the Pydantic-AI Agent made
                            pass

                response_message = create_message_from_run_input(
                    run_input=run_input,
                    id=message_id,
                    content=message_content,
                    role=Role.Assistant,
                    parent=parent_message_id,
                    tool_calls=message_tool_calls,
                    thinking=message_thinking,
                )

                mapped_messages.append(response_message)

            case _:
                assert_never(message)

    return mapped_messages
