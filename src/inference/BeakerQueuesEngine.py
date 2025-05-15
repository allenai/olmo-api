from collections.abc import Generator, Sequence
from dataclasses import asdict

from beaker import Beaker
from google.protobuf import json_format
from beaker.config import Config as BeakerConfig

from src.config.get_config import get_config
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
)

EXPIRES_IN = 60 * 60 * 24 * 30  # 30 days

class BeakerQueuesEngine(InferenceEngine):
    beaker_client: Beaker

    def __init__(self) -> None:
        cfg = get_config()
        self.beaker_client = Beaker(BeakerConfig(rpc_address=cfg.beaker.address, user_token=cfg.beaker.user_token))

    def create_streamed_message(
        self, model: str, messages: Sequence[InferenceEngineMessage], inference_options: InferenceOptions
    ) -> Generator[InferenceEngineChunk, None, None]:

        q = self.beaker_client.queue.get(model)
        input = {
            "model": q.id,
            "messages": [asdict(message) for message in messages],
            "stream": True,
            "opts": asdict(inference_options)
        }
        for m in self.beaker_client.queue.create_entry(q, input=input, expires_in_sec=EXPIRES_IN):
            if m.HasField("pending_entry"):
                pass
            if m.HasField("result"):
                result = json_format.MessageToDict(m.result)
                yield InferenceEngineChunk(content=result['choices'][0]['delta']['content'], model=model)
            if m.HasField("finalized_entry"):
                pass
