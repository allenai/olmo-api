import json
from dataclasses import asdict
from typing import Generator, Sequence

from grpc import Channel
from inferd import Client as InferdClient
from inferd.msg.inferd_pb2_grpc import InferDStub

from src import config, util
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceOptions,
    Logprob,
)
from src.message.create_message_service import InferenceEngineMessage


class InferDEngine(InferenceEngine):
    inferDClient: InferdClient
    inferd: InferDStub
    cfg: config.Config

    def __init__(self, cfg: config.Config, channel: Channel) -> None:
        self.inferDClient = InferdClient(cfg.inferd.address, cfg.inferd.token)
        self.inferd = InferDStub(channel)
        self.cfg = cfg

    def format_message(self, obj) -> str:
        return json.dumps(obj=obj, cls=util.CustomEncoder) + "\n"

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
                content=message["text"],
                model=model,
                logprobs=mapped_logprobs,
                finish_reason=message.get("finish_reason"),
            )
