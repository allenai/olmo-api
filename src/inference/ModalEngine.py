import base64
from dataclasses import asdict
from typing import Generator, Optional, Sequence

import modal
from werkzeug.datastructures import FileStorage

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

    def __get_args_for_model(
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

            image: Optional[str] = None
            if isinstance(messages[0], InferenceEngineMessageWithImage):
                new_message = messages[0]
                if isinstance(new_message.image, FileStorage):
                    image = base64.b64decode(new_message.image.stream.read()).decode()
                else:
                    image = new_message.image

            return [
                {
                    "prompt": modal_msgs,
                    # "image": "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=",
                    "image": image,
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
        args = self.__get_args_for_model(
            model=model, messages=messages, inference_options=inference_options
        )

        for chunk in f.remote_gen(*args):
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
