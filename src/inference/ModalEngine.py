import os
from typing import Generator, Sequence
from dataclasses import asdict

import modal

from src import config
from src.inference.InferenceEngine import (
    FinishReason,
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
    Logprob,
)

class ModalEngine(InferenceEngine):
    available_models: Sequence[config.Model]
    client: modal.Client

    def __init__(self) -> None:
        self.available_models = config.cfg.modal.available_models
        self.client = modal.Client.from_credentials(config.cfg.modal.token, config.cfg.modal.token_secret)

    def get_model_details(self, model_id: str) -> config.Model:
        model = next((m for m in self.available_models if m.id == model_id), None)
        return model

    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage],
        inference_options: InferenceOptions,
    ) -> Generator[InferenceEngineChunk, None, None]:
        f = modal.Function.lookup(model, "vllm_api", client=self.client)
        msgs = [asdict(msg) for msg in messages]
        opts = asdict(inference_options)
        
        for chunk in f.remote_gen(msgs, opts):
            content = (
                chunk["result"]["output"]["text"]
                if "result" in chunk and "output" in chunk["result"] and "text" in chunk["result"]["output"]
                else ""
            )

            logprobs = []

            yield InferenceEngineChunk(
                content=content,
                model=model,
                logprobs=logprobs,
            )
