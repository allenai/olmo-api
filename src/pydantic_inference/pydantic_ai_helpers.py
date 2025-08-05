from pydantic_ai.messages import (
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    SystemPromptPart,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
    UserContent,
    UserPromptPart,
)

from src.dao.message import Message, MessageChunk


def pydantic_map_chunk(chunk: PartStartEvent | PartDeltaEvent, message_id: str) -> MessageChunk:
    match chunk:
        case PartStartEvent():
            return pydantic_map_part(chunk.part, message_id)
        case PartDeltaEvent():
            return pydantic_map_delta(chunk.delta, message_id)


def pydantic_map_messages(messages: list[Message]) -> list[ModelMessage]:
    model_messages: list[ModelMessage] = []
    for message in messages:
        if message.role == "user":
            user_content: list[UserContent] = [message.content]
            for file in message.file_urls or []:
                user_content.append(ImageUrl(url=file))

            user_prompt_part = UserPromptPart(user_content)

            model_messages.append(ModelRequest([user_prompt_part]))
        elif message.role == "assistant":
            model_messages.append(
                ModelResponse(
                    parts=[TextPart(content=message.content)],
                )
            )
        elif message.role == "system":
            model_messages.append(ModelRequest([SystemPromptPart(message.content)]))

    return model_messages


def pydantic_map_part(part: TextPart | ToolCallPart | ThinkingPart, message_id: str) -> MessageChunk:
    match part:
        case TextPart():
            return MessageChunk(
                message=message_id,
                content=part.content,
            )
        case ThinkingPart():
            return MessageChunk(
                message=message_id,
                content=part.content or "",
            )
        case ToolCallPart():
            args_content = part.args or ""
            if isinstance(args_content, dict):
                args_content = str(args_content)

            return MessageChunk(
                message=message_id,
                content=args_content,
            )


def pydantic_map_delta(part: TextPartDelta | ToolCallPartDelta | ThinkingPartDelta, message_id: str) -> MessageChunk:
    match part:
        case TextPartDelta():
            return MessageChunk(
                message=message_id,
                content=part.content_delta,
            )
        case ThinkingPartDelta():
            return MessageChunk(
                message=message_id,
                content=part.content_delta or "",
            )
        case ToolCallPartDelta():
            # Convert args_delta to string if it's a dictionary
            args_content = part.args_delta or ""
            if isinstance(args_content, dict):
                args_content = str(args_content)

            return MessageChunk(
                message=message_id,
                content=f"TOOL {args_content} \n",
            )
