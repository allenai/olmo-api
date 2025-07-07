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

from openai import OpenAI
from src.config.get_config import cfg
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
)


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
        messages = [asdict(message) for message in messages]
        chat_completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            stream_options={
                "include_usage": False,
            },
        )
        for chunk in chat_completion:
            if len(chunk.choices) > 0:
                # Our API doesn't support choices, so choose the first.
                choice = chunk.choices[0]
                yield InferenceEngineChunk(
                    content=choice.delta.content,
                    finish_reason=choice.finish_reason,
                    id=chunk.id,
                    logprobs=choice.logprobs or [],
                    created=str(chunk.created),
                    model=model,
                )
            else:
                # According to the docs, if stream_options["include_usage"]=True, this can happen.
                # For now, we don't support this mode.
                raise NotImplementedError("chunks without choices are not yet supported")
