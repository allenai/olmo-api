import typing
from pathlib import Path

from pydantic_ai import VideoUrl
from pydantic_ai.messages import (
    AudioFormat,
    AudioUrl,
    BinaryContent,
    DocumentFormat,
    DocumentUrl,
    ImageFormat,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    MultiModalContent,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserContent,
    UserPromptPart,
    VideoFormat,
)
from src.dao.engine_models.message import Message
from src.dao.engine_models.tool_call import ToolCall
from src.dao.message.message_models import Role
from src.message.create_message_service.files import FileUploadResult


def _map_db_tool_to_pydantic_tool(tool: ToolCall):
    return ToolCallPart(tool_name=tool.tool_name, tool_call_id=tool.tool_call_id, args=tool.args)


VIDEO_FILE_EXTENSIONS = typing.get_args(VideoFormat)
DOCUMENT_FILE_EXTENSIONS = typing.get_args(DocumentFormat)
IMAGE_FILE_EXTENSIONS = typing.get_args(ImageFormat)
AUDIO_FILE_EXTENSIONS = typing.get_args(AudioFormat)


class UnsupportedMediaTypeError(Exception):
    pass


def _map_part_from_file_url(file_url: str, blob_map: dict[str, FileUploadResult] | None) -> MultiModalContent:
    if blob_map is not None and file_url in blob_map:
        return BinaryContent(
            data=blob_map[file_url].file_storage.stream.read(),
            media_type=blob_map[file_url].file_storage.content_type or "image/png",
        )

    file_suffix = Path(file_url).suffix

    if file_suffix.endswith(VIDEO_FILE_EXTENSIONS):
        return VideoUrl(url=file_url)

    if file_suffix.endswith(IMAGE_FILE_EXTENSIONS):
        return ImageUrl(url=file_url)

    if file_suffix.endswith(DOCUMENT_FILE_EXTENSIONS):
        return DocumentUrl(url=file_url)

    if file_suffix.endswith(AUDIO_FILE_EXTENSIONS):
        return AudioUrl(url=file_url)

    unsupported_media_type_msg = "File URL %s has unsupported media type %s"
    raise UnsupportedMediaTypeError(unsupported_media_type_msg, file_url, file_suffix)


def pydantic_map_messages(messages: list[Message], blob_map: dict[str, FileUploadResult] | None) -> list[ModelMessage]:
    model_messages: list[ModelMessage] = []
    for message in messages:
        if message.role == Role.User:
            file_user_content = [_map_part_from_file_url(file_url, blob_map) for file_url in message.file_urls or []]

            user_content: list[UserContent] = [message.content, *file_user_content]
            user_prompt_part = UserPromptPart(user_content)

            model_messages.append(ModelRequest([user_prompt_part]))
        elif message.role == Role.Assistant:
            assistant_message_parts: list[ModelResponsePart] = []

            if message.thinking is not None:
                assistant_message_parts.append(ThinkingPart(content=message.thinking))

            assistant_message_parts.append(TextPart(content=message.content))

            if message.tool_calls:
                assistant_message_parts.extend([_map_db_tool_to_pydantic_tool(tool) for tool in message.tool_calls])

            model_messages.append(
                ModelResponse(
                    parts=assistant_message_parts,
                )
            )
        elif message.role == Role.System:
            model_messages.append(ModelRequest([SystemPromptPart(message.content)]))
        elif message.role == Role.ToolResponse:
            if message.tool_calls is None:
                msg = "expected tool call in message"
                raise TypeError(msg)
            if len(message.tool_calls) != 1:
                msg = "expected exactly one tool in Tool Response Message"
                raise TypeError(msg)

            request_tool = message.tool_calls[0]

            model_messages.append(
                ModelRequest(
                    parts=[
                        ToolReturnPart(
                            tool_name=request_tool.tool_name,
                            tool_call_id=request_tool.tool_call_id,
                            content=message.content,
                        )
                    ]
                )
            )

    return model_messages


__all__ = ["pydantic_map_messages"]
