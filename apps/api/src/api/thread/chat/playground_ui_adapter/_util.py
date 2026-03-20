import copy
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
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
from core.message.flat_message import FlatMessage
from core.message.message_chunk import AddMessageChunk, ErrorChunk, FinalThreadChunk, StreamEndChunk, StreamStartChunk
from core.message.role import Role
from core.object_id import ID
from core.tools.tool_source import ToolSource
from db.models.inference_opts import InferenceOpts
from db.models.message import Message
from db.models.model_config import ModelConfig
from db.models.tool_call import ToolCall
from db.models.tool_definitions import ToolDefinition

__all__ = ["Event", "InputMessage", "RunInput"]


InputMessage: TypeAlias = Message
Event: TypeAlias = ChatStreamOutput


@dataclass
class RunInput:
    all_messages: Sequence[Message]
    new_messages: Sequence[Message]
    parent_message_id: ID
    root_message_id: ID
    creator: str
    inference_opts: InferenceOpts
    model: ModelConfig
    user_tool_names: Sequence[str]
    tool_definitions: list[ToolDefinition] | None
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
    error: ErrorChunk | None = None,
):
    message = Message(
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

    if error is not None:
        message.error_code = error.error_code
        message.error_description = error.error_description
        message.error_severity = error.error_severity

    return message


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
    messages: Sequence[ModelMessage], message_ids: Sequence[ID], run_input: RunInput, errors: Sequence[ErrorChunk]
) -> list[Message]:
    parent_message_id = run_input.parent_message_id
    split_messages = split_pydantic_messages(messages)

    mapped_messages: list[Message] = []
    for message_id, message in zip(message_ids, split_messages, strict=True):
        error: ErrorChunk | None = next((error for error in errors if error.message == message_id), None)

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
                            # We don't expect to have any other parts in the messages the Pydantic-AI Agent made
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
                    error=error,
                )

                mapped_messages.append(response_message)

            case _:
                assert_never(message)

        parent_message_id = message_id

    return mapped_messages


def split_pydantic_messages(
    messages: Sequence[ModelMessage],
) -> list[ModelMessage]:
    messages_without_system_message = [
        message for message in messages if not any(part.part_kind == "system-prompt" for part in message.parts)
    ]
    split_messages: list[ModelMessage] = []

    for message in messages_without_system_message:
        match message:
            case ModelRequest():
                request_without_tool_returns = copy.deepcopy(message)
                request_without_tool_returns.parts = [
                    part for part in message.parts if not isinstance(part, ToolReturnPart)
                ]
                if request_without_tool_returns.parts:
                    split_messages.append(request_without_tool_returns)

                # Our Messages have a separate message for each tool return
                # This breaks the tool returns into separate parts for us so we can map them more easily
                tool_return_parts = [part for part in message.parts if isinstance(part, ToolReturnPart)]
                for tool_return_part in tool_return_parts:
                    tool_return_model_request = ModelRequest(
                        parts=[tool_return_part],
                        timestamp=message.timestamp,
                        instructions=message.instructions,
                        kind=message.kind,
                        run_id=message.run_id,
                        metadata=message.metadata,
                    )
                    split_messages.append(tool_return_model_request)
            case _:
                split_messages.append(message)

    return split_messages


async def stream_pending_tool_responses(
    run_input: RunInput, handle_final_messages: Callable[[Sequence[Message]], Awaitable[Message]]
) -> AsyncIterator[Event]:
    """Short circuit the event stream and flush pending tool responses"""
    yield StreamStartChunk(message=run_input.root_message_id)

    new_flat = FlatMessage.from_message_seq(run_input.new_messages)
    yield AddMessageChunk(message=new_flat[0].id, id=new_flat[0].id, messages=new_flat)

    first_message = await handle_final_messages(run_input.new_messages)
    final_flat = FlatMessage.from_message_with_children(first_message)
    yield FinalThreadChunk(message=final_flat[0].id, id=final_flat[0].id, messages=final_flat)

    yield StreamEndChunk(message=run_input.new_messages[-1].id)
