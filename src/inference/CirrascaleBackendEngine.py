# Cirrascale maintains two APIs for their chat endpoints:
#
# 1. Consumer API that their website calls at https://ai2endpoints.cirrascale.ai/api
# 2. Set of backend APIs https://ai2models.cirrascalecloud.services:$PORT/v1
#    for each model on different ports.
#
# When requesting API tokens from accounts, the user receives a token that works for the Consumer API.
#
# Cirrascale has provided us an API token valid directly with the backend APIs
# that comes with a substantial allocation.
#

from collections.abc import Generator, Sequence
from dataclasses import asdict
from typing import TypeAlias, Literal

from openai.types.chat import ChatCompletionTokenLogprob
from openai.types.chat.chat_completion_token_logprob import TopLogprob
from openai import OpenAI
from src.config.get_config import cfg
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
    FinishReason,
    Logprob,
)

OpenAIFinishReason: TypeAlias = Literal["stop", "length", "tool_calls", "content_filter", "function_call"]


def map_openai_finish_reason(finish_reason: OpenAIFinishReason | None) -> FinishReason | None:
    match finish_reason:
        case "stop":
            return FinishReason.Stop
        case "length":
            return FinishReason.Length
        case "content_filter":
            return FinishReason.ValueError
        case None:
            return None
        case _:
            return FinishReason.Unknown


def map_openapi_top_logprob(top_logprob: TopLogprob) -> Logprob:
    # TODO: Make sure this is the right mapping for the token id.
    token_id = top_logprob.bytes[0] if top_logprob.bytes is not None else -1
    return Logprob(token_id=token_id, text=top_logprob.token, logprob=top_logprob.logprob)


def map_openai_logprobs(logprobs: list[ChatCompletionTokenLogprob] | None) -> Sequence[Sequence[Logprob]]:
    if logprobs is None:
        return []

    return [[map_openapi_top_logprob(top_logprob) for top_logprob in logprob.top_logprobs] for logprob in logprobs]


class CirrascaleBackendEngine(InferenceEngine):
    client: OpenAI
    model_name: str

    def __init__(self, model_name: str, *, port: str):
        self.model_name = model_name
        self.client = OpenAI(
            base_url=f"{cfg.cirrascale_backend.base_url}:{port}/v1",
            api_key=cfg.cirrascale_backend.api_key,
        )

    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage],
        inference_options: InferenceOptions,
    ) -> Generator[InferenceEngineChunk, None, None]:
        chat_messages = [asdict(message) for message in messages]  # type: ignore

        top_logprobs = 0
        if inference_options.logprobs is not None:
            top_logprobs = inference_options.logprobs

        chat_completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=chat_messages,  # type: ignore
            temperature=inference_options.temperature,
            max_tokens=inference_options.max_tokens,
            n=inference_options.n,
            top_p=inference_options.top_p,
            logprobs=top_logprobs > 0,
            top_logprobs=top_logprobs,
            stream=True,
            stream_options={"include_usage": False},
        )
        for chunk in chat_completion:
            # The calling API returns an error if n != 1, so it's safe to check for >0 here
            # and return the first if it exists.

            if len(chunk.choices) > 0:
                # Our API doesn't support choices, so choose the first.
                choice = chunk.choices[0]

                logprobs: Sequence[Sequence[Logprob]] = []
                if choice.logprobs is not None:
                    # TODO What should we do with the refusal logprob?
                    logprobs = map_openai_logprobs(choice.logprobs.content)

                yield InferenceEngineChunk(
                    content=choice.delta.content or "",
                    finish_reason=map_openai_finish_reason(choice.finish_reason),
                    id=chunk.id,
                    logprobs=logprobs,
                    created=str(chunk.created),
                    model=model,
                )
            else:
                # According to the docs, if stream_options["include_usage"]=True, this can happen.
                # For now, we don't support this mode.
                raise NotImplementedError("chunks without choices are not yet supported")
