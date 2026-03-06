from collections.abc import Sequence
from typing import NamedTuple

from fastapi import UploadFile
from pydantic_ai import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolReturnPart,
    UserContent,
    UserPromptPart,
)

from api.thread.chat.input_parts import map_input_parts
from core.message.role import Role
from db.models.message import Message


class MessageAndFiles(NamedTuple):
    message: Message
    files: Sequence[UploadFile] | Sequence[str] | None

    @staticmethod
    def from_message(message: Message):
        return MessageAndFiles(message=message, files=message.file_urls)


def _map_user_message(message: Message) -> ModelRequest:
    # file_user_content = [_map_part_from_file_url(file_url, blob_map) for file_url in message.file_urls or []]
    text_content = map_input_parts(message.input_parts, message.content)

    # user_content: list[UserContent] = [text_content, *file_user_content]
    user_content: list[UserContent] = [text_content]
    user_prompt_part = UserPromptPart(user_content)

    return ModelRequest([user_prompt_part])


def _map_assistant_message(message: Message) -> ModelResponse:
    assistant_message_parts: list[ModelResponsePart] = []

    if message.thinking is not None:
        assistant_message_parts.append(ThinkingPart(content=message.thinking))

    assistant_message_parts.append(TextPart(content=message.content))

    # if message.tool_calls:
    # assistant_message_parts.extend([_map_db_tool_to_pydantic_tool(tool) for tool in message.tool_calls])

    return ModelResponse(
        parts=assistant_message_parts,
    )


def _map_system_message(message: Message):
    return ModelRequest([SystemPromptPart(message.content)])


def _map_tool_response_message(message: Message):
    if message.tool_calls is None:
        msg = "expected tool call in message"
        raise TypeError(msg)

    if len(message.tool_calls) != 1:
        msg = "expected exactly one tool in Tool Response Message"
        raise TypeError(msg)

    request_tool = message.tool_calls[0]

    return ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name=request_tool.tool_name,
                tool_call_id=request_tool.tool_call_id,
                content=message.content,
            )
        ]
    )


class UnhandledRoleError(Exception): ...


def map_message(message: Message) -> ModelMessage:
    match message.role:
        case Role.User:
            return _map_user_message(message)
        case Role.Assistant:
            return _map_assistant_message(message)
        case Role.System:
            return _map_system_message(message)
        case Role.ToolResponse:
            return _map_tool_response_message(message)
        case _:
            unhandled_role_message = "Tried to map a message to Pydantic format for an unhandled role"
            raise UnhandledRoleError(unhandled_role_message)


# def pydantic_map_messages(messages: list[Message], blob_map: dict[str, FileUploadResult] | None) -> list[ModelMessage]:
def map_messages_to_pydantic_ai_format(messages: Sequence[Message]) -> list[ModelMessage]:
    return [map_message(message) for message in messages]
