from collections.abc import Sequence
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
from api.thread.chat.util import attach_message_children
from core.message.role import Role
from core.object_id import ID
from core.tools.tool_source import ToolSource
from db.models.inference_opts import InferenceOpts
from db.models.message import Message
from db.models.model_config import ModelConfig
from db.models.tool_call import ToolCall

__all__ = ["Event", "RunInput", "UIMessage"]


UIMessage: TypeAlias = Message
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
    user_tool_names: list[str]


def map_tool_return_part_to_message(
    part: ToolReturnPart, message_id: ID, parent_message_id: ID, run_input: RunInput
) -> UIMessage:
    message = Message(
        id=message_id,
        content=part.model_response_str(),
        role=Role.ToolResponse,
        creator=run_input.creator,
        opts=run_input.inference_opts,
        root=run_input.root_message_id,
        parent=parent_message_id,
        model_id=run_input.model.id,
        model_host=run_input.model.host,
        model_type=run_input.model.model_type,
        tool_calls=[
            ToolCall(
                tool_call_id=part.tool_call_id,
                tool_name=part.tool_name,
                tool_source=ToolSource.MCP,  # TODO: Figure out how to differentiate between internal and MCP tools
                args=None,
                message_id=message_id,
            )
        ],
    )

    return message


def map_tool_call_part_to_tool_call(part: BaseToolCallPart, message_id: ID, user_tool_names: list[str]) -> ToolCall:
    tool_source = (
        ToolSource.USER_DEFINED if part.tool_name in user_tool_names else ToolSource.MCP
    )  # TODO: Figure out how to tell if a tool is internal
    return ToolCall(
        tool_call_id=part.tool_call_id, tool_name=part.tool_name, tool_source=tool_source, message_id=message_id
    )


def map_response_pydantic_messages_to_messages(
    messages: Sequence[ModelMessage], message_ids: Sequence[ID], run_input: RunInput
):
    parent_message_id = run_input.parent_message_id

    mapped_messages: list[UIMessage] = []
    for i, message in enumerate(messages):
        message_id = message_ids[i]
        match message:
            case ModelRequest():
                for part in message.parts:
                    match part:
                        case ToolReturnPart():
                            tool_return_message = map_tool_return_part_to_message(
                                part, message_id=message_id, parent_message_id=parent_message_id, run_input=run_input
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

                for part in message.parts:
                    match part:
                        case TextPart():
                            message_content += part.content
                        case BaseToolCallPart():
                            tool_call = map_tool_call_part_to_tool_call(part, message_id, run_input.user_tool_names)
                            message_tool_calls.append(tool_call)
                        case ThinkingPart():
                            if message_thinking is None:
                                message_thinking = part.content
                            else:
                                message_thinking += part.content
                        case _:
                            # We don't expect to have any other parts in the the messages the Pydantic-AI Agent made
                            pass

                response_message = Message(
                    id=message_id,
                    content=message_content,
                    thinking=message_thinking,
                    creator=run_input.creator,
                    role=Role.Assistant,
                    opts=run_input.inference_opts,
                    root=run_input.root_message_id,
                    parent=parent_message_id,
                    model_id=run_input.model.id,
                    model_host=run_input.model.host,
                    model_type=run_input.model.model_type,
                )
                mapped_messages.append(response_message)

            case _:
                assert_never(message)

    return attach_message_children(mapped_messages)
