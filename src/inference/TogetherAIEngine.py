from dataclasses import asdict
from datetime import datetime
from typing import Generator, Iterator, Optional, Sequence

from together import Together
from together.types.chat_completions import ChatCompletionChoicesChunk
from together.types.common import FinishReason as TogetherFinishReason

from src import config
from src.inference.InferenceEngine import (
    FinishReason,
    InferenceEngine,
    InferenceEngineChunk,
    InferenceOptions,
    Logprob,
)
from src.message.create_message_service import InferenceEngineMessage


class TogetherAIEngine(InferenceEngine):
    togetherAIClient: Together

    def __init__(self, cfg: config.Config) -> None:
        self.togetherAIClient = Together(api_key=cfg.togetherai.api_key)
        print("Are u get initialized")

    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage],
        inference_options: InferenceOptions,
    ) -> Generator[InferenceEngineChunk, None, None]:
        print("Model")
        print(model)
        mapped_messages = [asdict(message) for message in messages]
        response = self.togetherAIClient.chat.completions.create(
            model=model,
            messages=mapped_messages,
            stream=True,
            **asdict(inference_options),
        )

        print("Inside TogetherAIEngine")
        print(response)

        if not isinstance(response, Iterator):
            raise NotImplementedError

        for chunk in response:
            if chunk.choices is None:
                raise NotImplementedError
            message = chunk.choices[0]
            content = (
                message.delta.content
                if message.delta is not None and message.delta.content is not None
                else ""
            )
            yield InferenceEngineChunk(
                content=content,
                model=model,
                logprobs= self.map_logprobs(message),
                finish_reason=self.map_finish_reason(message.finish_reason),
                created=datetime.fromtimestamp(chunk.created).isoformat()
                if chunk.created is not None
                else None,
            )

    def map_finish_reason(
        self, togetherAIFinishReason: Optional[TogetherFinishReason]
    ) -> Optional[FinishReason]:
        match togetherAIFinishReason:
            case TogetherFinishReason.Length:
                return FinishReason.Length
            case TogetherFinishReason.StopSequence:
                return FinishReason.Stop
            case TogetherFinishReason.EOS:
                return FinishReason.Aborted
            case _:
                return None

    def map_logprobs(
        self, togetherAIChunk: ChatCompletionChoicesChunk
    ) -> Sequence[Sequence[Logprob]]:
        if (
            togetherAIChunk.logprobs is None
            or togetherAIChunk.index is None
            or togetherAIChunk.delta is None
        ):
            return []

        return [
            [
                Logprob(
                    logprob=togetherAIChunk.logprobs,
                    text=togetherAIChunk.delta.content
                    if togetherAIChunk.delta is not None
                    and togetherAIChunk.delta.content is not None
                    else "",
                    token_id=togetherAIChunk.index,
                )
            ]
        ]
