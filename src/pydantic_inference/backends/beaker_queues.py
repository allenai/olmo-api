from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import assert_never

from beaker import Beaker
from beaker.beaker_pb2 import CreateQueueEntryResponse
from beaker.config import Config as BeakerConfig
from google.protobuf import json_format
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    ModelResponseStreamEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
)
from pydantic_ai.models import Model, ModelRequestParameters, StreamedResponse, check_allow_model_requests
from pydantic_ai.settings import ModelSettings

from src.config.get_config import get_config
from src.dao.engine_models.model_config import ModelConfig
from src.pydantic_inference.pydantic_ai_helpers import pydantic_reverse_map_messages

EXPIRES_IN = 60 * 60 * 24 * 30  # 30 days

MODEL_NO_RESPONSE_ERROR = "No response received from model"

def get_beaker_queues_model(model_config: ModelConfig) -> Model:
    return BeakerQueuesModel(model=model_config.model_id_on_host)

@dataclass(init=False)
class BeakerQueuesModel(Model):
    """Beaker Queues Model for Pydantic AI."""

    model: str
    beaker_client: Beaker
    _model_name: str = field(init=False)
    _system: str = field(default="system", init=False)

    def __init__(self, model: str, beaker_config: BeakerConfig | None = None) -> None:
        """Initialize the model with a beaker client."""
        if not beaker_config:
            cfg = get_config()
            beaker_config = BeakerConfig(rpc_address=cfg.beaker.address, user_token=cfg.beaker.user_token)

        self.model = model
        self._model_name = model
        self.beaker_client = Beaker(beaker_config)

    # Sync 
    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """Make a request to the model. (NotImplemented), streaming only"""
        raise NotImplementedError

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,  # noqa: ARG002
    ):
        """Make a streaming request to the model."""
        check_allow_model_requests()  # Required for testing
        q = self.beaker_client.queue.get(self._model_name)

        new_messages = pydantic_reverse_map_messages(messages)
        queue_input = {
            "model": q.id,
            "messages": new_messages,
            "stream": True,
            **(model_settings or {}),
        }

        entry = self.beaker_client.queue.create_entry(q, input=queue_input, expires_in_sec=EXPIRES_IN)

        stream = BeakerQueuesStreamedResponse(
            _model_name=self._model_name,
            _queue_entry=entry,
        )

        yield stream

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def system(self) -> str:
        return self._system


@dataclass
class BeakerQueuesStreamedResponse(StreamedResponse):
    """A stream response from Beaker Queues."""

    _model_name: str
    _queue_entry: Iterable[CreateQueueEntryResponse]
    _timestamp: datetime = field(default_factory=lambda: datetime.now(UTC), init=False)

    # Roughly from BeakerQueuesEngine
    async def _get_event_iterator(self) -> AsyncIterator[ModelResponseStreamEvent]:
        for index, resp in enumerate(self._queue_entry):

            if resp.HasField("pending_entry"):
                # Is this needed?
                yield PartStartEvent(index=0, part=TextPart(content=""))
            elif resp.HasField("result"):
                result = json_format.MessageToDict(resp.result)
                # Only handling content
                content = result["choices"][0]["delta"]["content"]
                yield PartDeltaEvent(index=index, delta=TextPartDelta(content_delta=content))
            elif resp.HasField("finalized_entry"):
                # Do something?
                pass
            else:
                assert_never(resp)  # type: ignore

    # Required properties on StreamedResponse(ABC)
    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def timestamp(self) -> datetime:
        return self._timestamp
