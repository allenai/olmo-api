from pydantic_ai.messages import (
    BinaryContent,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    PartDeltaEvent,
    PartStartEvent,
    SystemPromptPart,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
    ToolReturnPart,
    UserContent,
    UserPromptPart,
)

from src.dao.message import Message, Role
from src.message.create_message_service.files import FileUploadResult
from src.message.message_chunk import Chunk, ModelResponseChunk, ThinkingChunk, ToolCallChunk


def pydantic_map_chunk(chunk: PartStartEvent | PartDeltaEvent, message_id: str) -> Chunk:
    match chunk:
        case PartStartEvent():
            return pydantic_map_part(chunk.part, message_id)
        case PartDeltaEvent():
            return pydantic_map_delta(chunk.delta, message_id)


def pydantic_map_messages(messages: list[Message], blob_map: dict[str, FileUploadResult]) -> list[ModelMessage]:
    model_messages: list[ModelMessage] = []
    for message in messages:
        if message.role == Role.User:
            user_content: list[UserContent] = [message.content]
            for file_url in message.file_urls or []:
                if file_url in blob_map:
                    user_content.append(
                        BinaryContent(
                            data=blob_map[file_url].file_storage.stream.read(),
                            media_type=blob_map[file_url].file_storage.content_type or "image/png",
                        )
                    )
                else:
                    user_content.append(ImageUrl(url=file_url))

            user_prompt_part = UserPromptPart(user_content)

            model_messages.append(ModelRequest([user_prompt_part]))
        elif message.role == Role.Assistant:
            assistant_message_parts: list[ModelResponsePart] = []

            if message.thinking is not None:
                assistant_message_parts.append(ThinkingPart(content=message.thinking))

            assistant_message_parts.append(TextPart(content=message.content))

            if message.tool_calls:
                assistant_message_parts.extend(message.tool_calls)

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


def pydantic_map_part(part: ModelResponsePart, message_id: str) -> Chunk:
    match part:
        case TextPart():
            return ModelResponseChunk(
                message=message_id,
                content=part.content,
            )
        case ThinkingPart():
            return ThinkingChunk(
                message=message_id,
                content=part.content or "",
            )
        case ToolCallPart():
            return ToolCallChunk(
                message=message_id, tool_call_id=part.tool_call_id, tool_name=part.tool_name, args=part.args
            )
        case _:
            msg = "unsupported response part"
            raise NotImplementedError(msg)


def pydantic_map_delta(part: TextPartDelta | ToolCallPartDelta | ThinkingPartDelta, message_id: str) -> Chunk:
    match part:
        case TextPartDelta():
            return ModelResponseChunk(message=message_id, content=part.content_delta or "")
        case ThinkingPartDelta():
            return ThinkingChunk(message=message_id, content=part.content_delta or "")
        case ToolCallPartDelta():
            return ToolCallChunk(
                message=message_id,
                tool_call_id=part.tool_call_id or "",
                tool_name=part.tool_name_delta or "",
                args=part.args_delta,
            )
