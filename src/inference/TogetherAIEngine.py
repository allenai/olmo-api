from dataclasses import asdict
from datetime import datetime
from math import ceil
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

UNLIKELY_LOGPROB = -9999.0


class TogetherAIEngine(InferenceEngine):
    togetherAIClient: Together

    def __init__(self, cfg: config.Config) -> None:
        self.togetherAIClient = Together(api_key=cfg.togetherai.token)

    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage],
        inference_options: InferenceOptions,
    ) -> Generator[InferenceEngineChunk, None, None]:
        if inference_options.max_tokens is not None:
            contents_length = sum([len(message.content) for message in messages])

            # HACK: There's ways to do this more precisely but dividing by 2 then adding 10 seems to get us close
            rough_token_count = ceil(contents_length / 2) + 10

            inference_options.max_tokens = (
                inference_options.max_tokens - rough_token_count
            )

        enable_logprobs = (
            inference_options.logprobs is not None and inference_options.logprobs > 0
        )
        # Together doesn't accept anything more than 1 (a bool value) for logprobs
        # To get an equivalent response we ask for n potential completions (n == inference_options.logprobs) and map from there
        if enable_logprobs:
            inference_options.logprobs = 1

        mapped_messages = [asdict(message) for message in messages]

        response = self.togetherAIClient.chat.completions.create(
            model=model,
            messages=mapped_messages,
            stream=True,
            **asdict(inference_options),
        )

        if not isinstance(response, Iterator):
            raise TypeError("Together returned a non-streamed response")

        for chunk in response:
            if chunk.choices is None:
                raise NotImplementedError

            message = chunk.choices[0]
            content = (
                message.delta.content
                if message.delta is not None and message.delta.content is not None
                else ""
            )

            mapped_logprobs = (
                self.map_logprobs(chunk.choices) if enable_logprobs is True else []
            )
            created = (
                datetime.fromtimestamp(chunk.created).isoformat()
                if chunk.created is not None
                else None
            )

            yield InferenceEngineChunk(
                content=content,
                model=model,
                logprobs=mapped_logprobs,
                finish_reason=self.map_finish_reason(message.finish_reason),
                created=created,
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
        self, togetherAIChunk: list[ChatCompletionChoicesChunk]
    ) -> Sequence[Sequence[Logprob]]:
        return [
            [
                Logprob(
                    logprob=chunk.logprobs
                    if chunk.logprobs is not None
                    else UNLIKELY_LOGPROB,
                    token_id=chunk.delta.token_id,  # type: ignore - this token_id exists in the response but not in the Python typing
                    text=chunk.delta.content
                    if chunk.delta is not None and chunk.delta.content is not None
                    else "",
                )
                for chunk in togetherAIChunk
            ]
        ]
