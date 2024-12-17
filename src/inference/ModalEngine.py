from dataclasses import asdict
from typing import Generator, Sequence

import modal

from src import config
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceEngineMessageWithImage,
    InferenceOptions,
    Logprob,
)


class ModalEngine(InferenceEngine):
    available_models: Sequence[config.Model]
    client: modal.Client

    def __init__(self) -> None:
        self.available_models = config.cfg.modal.available_models
        self.client = modal.Client.from_credentials(
            config.cfg.modal.token, config.cfg.modal.token_secret
        )

    def get_model_details(self, model_id: str) -> config.Model:
        model = next((m for m in self.available_models if m.id == model_id), None)
        return model

    def __get_opts_for_model(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage | InferenceEngineMessageWithImage],
        inference_options: InferenceOptions,
    ):
        if model == "mm-olmo-uber-model-v4-synthetic":
            modal_msgs = (
                " ".join([f"{message.role}: {message.content}" for message in messages])
                + "Assistant:"
            )

            return [
                {
                    "prompt": modal_msgs,
                    "image": (
                        messages[0].image
                        if isinstance(messages[0], InferenceEngineMessageWithImage)
                        else None
                    ),
                    "opts": asdict(inference_options),
                }
            ]
        else:
            msgs = [asdict(msg) for msg in messages]
            opts = asdict(inference_options)
            return [msgs, opts]

    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage | InferenceEngineMessageWithImage],
        inference_options: InferenceOptions,
    ) -> Generator[InferenceEngineChunk, None, None]:
        f = modal.Function.lookup(model, "vllm_api", client=self.client)
        msgs = [asdict(msg) for msg in messages]
        opts = asdict(inference_options)

        for chunk in f.remote_gen(msgs, opts):
            content = chunk.get("result", {}).get("output", {}).get("text", "")

            logprobs: Sequence[Sequence[Logprob]] = []

            inputTokenCount = chunk.get("result", {}).get("inputTokenCount", -1)
            outputTokenCount = chunk.get("result", {}).get("outputTokenCount", -1)

            yield InferenceEngineChunk(
                content=content,
                model=model,
                logprobs=logprobs,
                input_token_count=inputTokenCount,
                output_token_count=outputTokenCount,
            )
