import base64

from pydantic_ai.messages import (
    BinaryContent,
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
                if isinstance(file, str):
                    user_content.append(ImageUrl(url=file))
                else:
                    # TODO: not sure about this... copied from ModalEngine.py
                    image_bytes = base64.b64encode(file.stream.read())
                    user_content.append(BinaryContent(image_bytes, media_type=file.mimetype))

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
    mapped_logprobs = []  # TODO: Depracated property

    match part:
        case TextPart():
            return MessageChunk(
                message=message_id,
                content=part.content,
                logprobs=mapped_logprobs,
            )
        case ThinkingPart():
            return MessageChunk(
                message=message_id,
                content=part.content or "",
                logprobs=mapped_logprobs,
            )
        case ToolCallPart():
            return MessageChunk(
                message=message_id,
                content=part.part_kind or "",
                logprobs=mapped_logprobs,
            )


def pydantic_map_delta(part: TextPartDelta | ToolCallPartDelta | ThinkingPartDelta, message_id: str) -> MessageChunk:
    mapped_logprobs = []  # TODO: Depracated property

    match part:
        case TextPartDelta():
            return MessageChunk(
                message=message_id,
                content=part.content_delta,
                logprobs=mapped_logprobs,
            )
        case ThinkingPartDelta():
            return MessageChunk(
                message=message_id,
                content=part.content_delta or "",
                logprobs=mapped_logprobs,
            )
        case ToolCallPartDelta():
            # Convert args_delta to string if it's a dictionary
            args_content = part.args_delta or ""
            if isinstance(args_content, dict):
                args_content = str(args_content)

            return MessageChunk(
                message=message_id,
                content=f"TOOL: {args_content} \n",
                logprobs=mapped_logprobs,
            )
