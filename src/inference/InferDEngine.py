from collections.abc import Generator, Sequence
from dataclasses import asdict

from inferd import Client as InferdClient

from src.config import Model, cfg
from src.config.get_models_by_host import get_models_by_host
from src.config.ModelConfig import ModelHost
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
    Logprob,
)


class InferDEngine(InferenceEngine):
    inferDClient: InferdClient
    available_models: Sequence[Model]

    def __init__(self) -> None:
        self.inferDClient = InferdClient(cfg.inferd.address, cfg.inferd.token)
        self.available_models = get_models_by_host(ModelHost.InferD)

    def get_model_details(self, model_id: str) -> Model | None:
        model = next((m for m in self.available_models if m.id == model_id), None)
        return model

    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage],
        inference_options: InferenceOptions,
    ) -> Generator[InferenceEngineChunk, None, None]:
        request = {
            "messages": [asdict(message) for message in messages],
            "opts": asdict(inference_options),
        }

        for message in self.inferDClient.infer(model, payload=request):
            logprobs = message.get("logprobs")
            mapped_logprobs = (
                [
                    [
                        Logprob(
                            # For some reason InferDClient returns token_id as a float instead of an int.
                            # it should always be an int so we're converting it here
                            token_id=int(lp["token_id"]),
                            text=lp["text"],
                            logprob=lp["logprob"],
                        )
                        for lp in lp_list
                    ]
                    for lp_list in logprobs
                ]
                if logprobs is not None
                else []
            )

            yield InferenceEngineChunk(
                content=message.get("text") or "",
                model=model,
                logprobs=mapped_logprobs,
                finish_reason=message.get("finish_reason"),
            )
