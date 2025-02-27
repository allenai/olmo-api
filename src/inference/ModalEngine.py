import base64
from collections.abc import Generator, Sequence
from dataclasses import asdict

import modal
from werkzeug.datastructures import FileStorage

from src.config.Config import Model
from src.config.get_config import cfg
from src.config.get_models_by_host import get_models_by_host
from src.config.ModelConfig import ModelHost
from src.dao.message import Role
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
    Logprob,
)


class ModalEngine(InferenceEngine):
    available_models: Sequence[Model]
    client: modal.Client

    def __init__(self) -> None:
        self.available_models = get_models_by_host(ModelHost.Modal)
        self.client = modal.Client.from_credentials(cfg.modal.token, cfg.modal.token_secret)

    def get_model_details(self, model_id: str) -> Model | None:
        return next((m for m in self.available_models if m.id == model_id), None)

    def __get_args_for_model(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage],
        inference_options: InferenceOptions,
    ):
        if model == "mm-olmo-uber-model-v4-synthetic":
            modal_msgs = " ".join([f"{message.role}: {message.content}" for message in messages]) + "Assistant:"

            image: str | None = None
            # TODO: This only supports sending files in the first message. We'll need to change this in the future if it supports sending files in each message
            first_user_message = next(message for message in messages if message.role == Role.User)

            if first_user_message.files is not None and len(first_user_message.files) > 0:
                if isinstance(first_user_message.files[0], FileStorage):
                    image = base64.b64encode(first_user_message.files[0].stream.read()).decode()
                else:
                    image = first_user_message.files[0]

            return [
                {
                    "prompt": modal_msgs,
                    "image": image,
                    "opts": asdict(inference_options),
                }
            ]

        # Modal doesn't like additional arguments, especially 'files'
        # We prevent it from showing up by filtering anything with None
        # This isn't a problem with the UI but it shows up in e2e tests
        msgs = [{k: v for k, v in asdict(msg).items() if v is not None} for msg in messages]
        opts = asdict(inference_options)
        return [msgs, opts]

    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage],
        inference_options: InferenceOptions,
    ) -> Generator[InferenceEngineChunk, None, None]:
        f = modal.Function.lookup(model, "vllm_api", client=self.client)
        args = self.__get_args_for_model(model=model, messages=messages, inference_options=inference_options)

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
