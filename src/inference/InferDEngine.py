import json
from dataclasses import asdict
from typing import Generator, List, Optional

from inferd import Client as InferdClient

from src import config, util
from src.inference.InferenceEngine import InferenceEngine, InferenceEngineChunk
from src.message.create_message_service import InferenceEngineMessage


class InferDEngine(InferenceEngine):
    inferDClient: InferdClient

    def __init__(self, cfg: config.Config) -> None:
        self.inferDClient = InferdClient(cfg.inferd.address, cfg.inferd.token)

    def format_message(self, obj) -> str:
        return json.dumps(obj=obj, cls=util.CustomEncoder) + "\n"

    def create_streamed_message(
        self,
        model: str,
        messages: List[InferenceEngineMessage],
        max_tokens: Optional[int] = None,
        stop_words: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        logprobs: Optional[int] = None,
    ) -> Generator[InferenceEngineChunk, None, None]:
        request = {
            "messages": [asdict(message) for message in messages],
            "opts": {
                "max_tokens": max_tokens,
                "stop_words": stop_words,
                "temperature": temperature,
                "top_p": top_p,
                "logprobs": logprobs,
            },
        }

        for message in self.inferDClient.infer(model, payload=request):
            print(message)
            yield InferenceEngineChunk(
                content=message["text"],
                model=model,
                logprobs=message.get("logprobs"),
                finish_reason=message.get("finish_reason"),
            )
