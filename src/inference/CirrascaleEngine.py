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
from src.dao.engine_models import ModelConfig
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
)

# This is the list of ports on which various models are hosted using on the ai2endpoints backend APIs.
# Cirrascale should provide us these values when they add models.
model_to_cirrascale_port = {
    "OLMo-2-0425-1B-Instruct": 22501,
    "OLMo-2-1124-7B-Instruct": 22502,
    "OLMo-2-1124-13B-Instruct": 22503,
    "OLMo-2-0325-32B-Instruct": 22504,
    "Llama-3.1-Tulu-3.1-8B": 22505,
    "Llama-3.1-Tulu-3-70B": 22506,
    "Molmo-7B-D-0924": 22507
}

class CirrascaleEngine(InferenceEngine):
    client: OpenAI
    model_name: str

    def __init__(self, model_name: str):
        port = model_to_cirrascale_port.get(model_name, None)
        if port is None:
            raise ValueError(f"Cirrascale does not support model {model_name}")
        self.model_name = model_name
        self.client = OpenAI(
            base_url=f"{cfg.cirrascale.base_url}:{port}/v1",
            api_key=cfg.cirrascale.api_key,
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
                choice=chunk.choices[0]
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

