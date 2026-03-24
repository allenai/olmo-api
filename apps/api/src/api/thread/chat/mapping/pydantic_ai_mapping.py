from collections.abc import Sequence
from mimetypes import guess_type

from pydantic_ai import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    ModelMessage,
    ModelRequestPart,
    ModelResponsePart,
    MultiModalContent,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserContent,
    UserPromptPart,
    VideoUrl,
)
from pydantic_ai.ui import MessagesBuilder

# We need to use the starlette UploadFile because FastAPI's UploadFile and the actual UploadFile type we get from the request are different
# https://github.com/fastapi/fastapi/discussions/13208
from starlette.datastructures import UploadFile

from api.thread.chat.chat_exceptions import UnhandledRoleError, UnsupportedMediaTypeError
from api.thread.chat.mapping.input_parts import map_input_parts
from core.message.role import Role
from db.models.message import Message
from db.models.tool_call import ToolCall


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


def _map_user_message(message: Message) -> ModelRequestPart:
    text_content = map_input_parts(message.input_parts, message.content)
    user_content: list[UserContent] = [text_content]

    file_content = [_map_part_from_file(file) for file in message.file_urls] if message.file_urls is not None else None
    if file_content:
        user_content += file_content

    user_prompt_part = UserPromptPart(user_content)
    return user_prompt_part


def _map_db_tool_to_pydantic_tool(tool: ToolCall):
    return ToolCallPart(tool_name=tool.tool_name, tool_call_id=tool.tool_call_id, args=tool.args)


def _map_assistant_message(message: Message) -> list[ModelResponsePart]:
    assistant_message_parts: list[ModelResponsePart] = []

    if message.thinking is not None:
        assistant_message_parts.append(ThinkingPart(content=message.thinking))

    assistant_message_parts.append(TextPart(content=message.content))

    if message.tool_calls:
        assistant_message_parts.extend([_map_db_tool_to_pydantic_tool(tool) for tool in message.tool_calls])

    return assistant_message_parts


def _map_system_message(message: Message) -> ModelRequestPart:
    return SystemPromptPart(message.content)


def _map_tool_response_message(message: Message):
    if message.tool_calls is None:
        msg = "expected tool call in message"
        raise TypeError(msg)

    if len(message.tool_calls) != 1:
        msg = "expected exactly one tool in Tool Response Message"
        raise TypeError(msg)

    request_tool = message.tool_calls[0]

    return ToolReturnPart(
        tool_name=request_tool.tool_name,
        tool_call_id=request_tool.tool_call_id,
        content=message.content,
    )


def map_message_to_part(message: Message) -> list[ModelRequestPart] | list[ModelResponsePart]:
    match message.role:
        case Role.User:
            return [_map_user_message(message)]
        case Role.Assistant:
            return _map_assistant_message(message)
        case Role.System:
            return [_map_system_message(message)]
        case Role.ToolResponse:
            return [_map_tool_response_message(message)]
        case _:
            unhandled_role_message = "Tried to map a message to Pydantic format for an unhandled role"
            raise UnhandledRoleError(unhandled_role_message)


def map_messages_to_pydantic_ai_format(messages: Sequence[Message]) -> list[ModelMessage]:
    part_lists = [map_message_to_part(message) for message in messages]
    parts = [part for parts in part_lists for part in parts]

    builder = MessagesBuilder()

    for part in parts:
        builder.add(part)

    mapped_messages = builder.messages

    # There's a bug with Pydantic AI where they give messages a run ID if the run ID is None
    # This causes issues when they're computing what messages in a run are new
    # If there's only one message they'll assume it's part of this run and include it in the new messages
    # To work around that, we give this a fake run_id
    for mapped_message in mapped_messages:
        mapped_message.run_id = messages[0].id

    return mapped_messages
