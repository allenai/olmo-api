from collections.abc import Sequence
import base64

from src.inference.InferenceEngine import (
    InferenceEngineMessage,
)
from pydantic_ai.messages import (
    BinaryContent,
    ImageUrl,
    PartStartEvent,
    PartDeltaEvent,
    ModelMessage,
    ModelRequest,
    UserContent,
    UserPromptPart,
    ModelResponse,
    TextPart,
    SystemPromptPart,
    TextPartDelta,
    ThinkingPartDelta,
    ToolCallPartDelta,
    ThinkingPart,
    ToolCallPart,
)
from src.dao import message


def pydantic_map_chunk(chunk: PartStartEvent | PartDeltaEvent, message_id: str) -> message.MessageChunk:
    match chunk:
        case PartStartEvent():
            return pydantic_map_part(chunk.part, message_id)
        case PartDeltaEvent():
            return pydantic_map_delta(chunk.delta, message_id)


def pydantic_map_messages(
    messages: Sequence[InferenceEngineMessage],
) -> list[ModelMessage]:
    # TODO FILES / Images

    model_messages: list[ModelMessage] = []
    for message in messages:
        if message.role == "user":
            user_content: list[UserContent] = [message.content]
            for file in message.files or []:
                if isinstance(file, str):
                    user_content.append(ImageUrl(url='https://iili.io/3Hs4FMg.png'))
                else:
                    # TODO not sure about this... copied from ModalEngine.py
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

def pydantic_map_part(part: TextPart | ToolCallPart | ThinkingPart, message_id: str) -> message.MessageChunk:
    mapped_logprobs = [] # TODO Depracated property

    match part:
        case TextPart():
            return message.MessageChunk(
                message=message_id,
                content=part.content,
                logprobs=mapped_logprobs,
            )
        case ThinkingPart():
            return message.MessageChunk(
                message=message_id,
                content=part.content or "",
                logprobs=mapped_logprobs,
            )
        case ToolCallPart():
            return message.MessageChunk(
                message=message_id,
                content=part.part_kind or "",
                logprobs=mapped_logprobs,
            )
        case _:
            raise ValueError(f"Unknown part type: {type(part)}")
        

def pydantic_map_delta(part: TextPartDelta | ToolCallPartDelta | ThinkingPartDelta, message_id: str) -> message.MessageChunk:
    mapped_logprobs = [
        [message.TokenLogProbs(token_id=lp.token_id, text=lp.text, logprob=lp.logprob) for lp in lp_list]
        for lp_list in []  # TODO: replace with actual logprobs from pydantic inference engine
    ]

    match part:
        case TextPartDelta():
            return message.MessageChunk(
                message=message_id,
                content=part.content_delta,
                logprobs=mapped_logprobs,
            )
        case ThinkingPartDelta():
            return message.MessageChunk(
                message=message_id,
                content=part.content_delta or "",
                logprobs=mapped_logprobs,
            )
        case ToolCallPartDelta():
            return message.MessageChunk(
                message=message_id,
                content=part.part_delta_kind or "",
                logprobs=mapped_logprobs,
            )
        case _:
            raise ValueError(f"Unknown part type: {type(part)}")
