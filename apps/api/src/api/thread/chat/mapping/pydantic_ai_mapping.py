from collections.abc import Sequence
from mimetypes import guess_type
from typing import NamedTuple

from fastapi import UploadFile
from pydantic_ai import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    MultiModalContent,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolReturnPart,
    UserContent,
    UserPromptPart,
    VideoUrl,
)

from api.thread.chat.chat_exceptions import UnhandledRoleError, UnsupportedMediaTypeError
from api.thread.chat.mapping.input_parts import map_input_parts
from core.message.role import Role
from db.models.message import Message


class MessageAndFiles(NamedTuple):
    """Named tuple that handles the message -> files mapping"""

    message: Message
    files: Sequence[UploadFile] | Sequence[str] | None

    @staticmethod
    def from_message(message: Message):
        return MessageAndFiles(message=message, files=message.file_urls)


def _map_part_from_file(file: str | UploadFile) -> MultiModalContent:
    if isinstance(file, UploadFile):
        return BinaryContent(data=file.file.read(), media_type=file.content_type or "")

    (mimetype, _encoding) = guess_type(file)

    match mimetype:
        case None:
            # Defaulting to Image for now since most of our uploads are images
            # We can error if we enforce file extensions on upload
            return ImageUrl(file)

        case mimetype if mimetype.startswith("video"):
            return VideoUrl(file)

        case mimetype if mimetype.startswith("image"):
            return ImageUrl(file)

        case mimetype if mimetype.startswith(("text", "application")):
            return DocumentUrl(file)

        case mimetype if mimetype.startswith("audio"):
            return AudioUrl(file)

    unsupported_media_type_msg = f"File URL {file} has unsupported MIME type {mimetype}"
    raise UnsupportedMediaTypeError(unsupported_media_type_msg)


def _map_user_message(message_and_files: MessageAndFiles) -> ModelRequest:
    text_content = map_input_parts(message_and_files.message.input_parts, message_and_files.message.content)
    user_content: list[UserContent] = [text_content]

    file_content = (
        [_map_part_from_file(file) for file in message_and_files.files] if message_and_files.files is not None else None
    )
    if file_content:
        user_content += file_content

    user_prompt_part = UserPromptPart(user_content)

    return ModelRequest([user_prompt_part])


def _map_assistant_message(message_and_files: MessageAndFiles) -> ModelResponse:
    assistant_message_parts: list[ModelResponsePart] = []

    if message_and_files.message.thinking is not None:
        assistant_message_parts.append(ThinkingPart(content=message_and_files.message.thinking))

    assistant_message_parts.append(TextPart(content=message_and_files.message.content))

    # if message.tool_calls:
    # assistant_message_parts.extend([_map_db_tool_to_pydantic_tool(tool) for tool in message.tool_calls])

    return ModelResponse(
        parts=assistant_message_parts,
    )


def _map_system_message(message_and_files: MessageAndFiles):
    return ModelRequest([SystemPromptPart(message_and_files.message.content)])


def _map_tool_response_message(message_and_files: MessageAndFiles):
    if message_and_files.message.tool_calls is None:
        msg = "expected tool call in message"
        raise TypeError(msg)

    if len(message_and_files.message.tool_calls) != 1:
        msg = "expected exactly one tool in Tool Response Message"
        raise TypeError(msg)

    request_tool = message_and_files.message.tool_calls[0]

    return ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name=request_tool.tool_name,
                tool_call_id=request_tool.tool_call_id,
                content=message_and_files.message.content,
            )
        ]
    )


def map_message(message_and_files: MessageAndFiles) -> ModelMessage:
    match message_and_files.message.role:
        case Role.User:
            return _map_user_message(message_and_files)
        case Role.Assistant:
            return _map_assistant_message(message_and_files)
        case Role.System:
            return _map_system_message(message_and_files)
        case Role.ToolResponse:
            return _map_tool_response_message(message_and_files)
        case _:
            unhandled_role_message = "Tried to map a message to Pydantic format for an unhandled role"
            raise UnhandledRoleError(unhandled_role_message)


def map_messages_to_pydantic_ai_format(messages: Sequence[MessageAndFiles]) -> list[ModelMessage]:
    return [map_message(message) for message in messages]
