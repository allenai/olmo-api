from collections.abc import Sequence

from src.inference.InferenceEngine import (
    InferenceEngineMessage,
)
from pydantic_ai.messages import (
    PartStartEvent,
    PartDeltaEvent,
    ModelMessage,
    ModelRequest,
    UserPromptPart,
    ModelResponse,
    ModelResponsePart,
    TextPart,
    SystemPromptPart,
    TextPartDelta,
    ThinkingPartDelta,
    ToolCallPartDelta,
)
from src.dao import message


def pydantic_map_chunk(chunk: PartStartEvent | PartDeltaEvent, message_id: str) -> message.MessageChunk:
    mapped_logprobs = [
        [message.TokenLogProbs(token_id=lp.token_id, text=lp.text, logprob=lp.logprob) for lp in lp_list]
        for lp_list in []  # TODO: replace with actual logprobs from pydantic inference engine
    ]

    match chunk:
        case PartStartEvent():
            # TODO learn more about this first start event. Maybe can ignore...
            return message.MessageChunk(
                message=message_id,
                content="",
                logprobs=mapped_logprobs,
            )
        case PartDeltaEvent():
            match chunk.delta:
                case TextPartDelta():
                    return message.MessageChunk(
                        message=message_id,
                        content=chunk.delta.content_delta,
                        logprobs=mapped_logprobs,
                    )
                case ThinkingPartDelta():
                    return message.MessageChunk(
                        message=message_id,
                        content=chunk.delta.content_delta or "",
                        logprobs=mapped_logprobs,
                    )
                case ToolCallPartDelta():
                    return message.MessageChunk(
                        message=message_id,
                        content=chunk.delta.part_delta_kind or "",
                        logprobs=mapped_logprobs,
                    )


def pydantic_map_messages(
    messages: Sequence[InferenceEngineMessage],
) -> list[ModelMessage]:
    # TODO FILES

    model_messages: list[ModelMessage] = []
    for message in messages:
        if message.role == "user":
            model_messages.append(ModelRequest([UserPromptPart(message.content)]))
        elif message.role == "assistant":
            model_messages.append(
                ModelResponse(
                    parts=[TextPart(content=message.content)],
                )
            )
        elif message.role == "system":
            model_messages.append(ModelRequest([SystemPromptPart(message.content)]))

    return model_messages
