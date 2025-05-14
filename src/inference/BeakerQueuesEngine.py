from collections.abc import Generator, Sequence
from dataclasses import asdict

from beaker import Beaker
from beaker.config import Config as BeakerConfig

from src.config.get_config import get_config
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
)


class BeakerQueuesEngine(InferenceEngine):
    beaker_client: Beaker

    def __init__(self) -> None:
        cfg = get_config()
        self.beaker_client = Beaker(BeakerConfig(user_token=cfg.beaker.user_token))

    def create_streamed_message(
        self, model: str, messages: Sequence[InferenceEngineMessage], inference_options: InferenceOptions
    ) -> Generator[InferenceEngineChunk, None, None]:
        request = {
            "queue_id": model,
            "async": False,
            "input": {"messages": [asdict(message) for message in messages], "opts": asdict(inference_options)},
        }

        for message in self.beaker_client.create_queue_entry(request):
            # handle QueueEntry for start/end
            yield InferenceEngineChunk(content=message.get("text"), model=model)
