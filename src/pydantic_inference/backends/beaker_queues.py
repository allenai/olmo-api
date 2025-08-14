from collections.abc import AsyncIterable, AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from beaker import Beaker
from beaker.config import Config as BeakerConfig
from google.protobuf import json_format
from openai.types.chat import ChatCompletionChunk
from pydantic_ai.messages import (
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import Model, ModelRequestParameters, check_allow_model_requests
from pydantic_ai.models.openai import OpenAIStreamedResponse
from pydantic_ai.settings import ModelSettings

from src.config.get_config import get_config
from src.dao.engine_models.model_config import ModelConfig

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

    # non streaming, not implemented 
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
    ) -> AsyncIterator[OpenAIStreamedResponse]:
        """Make a streaming request to the model."""
        check_allow_model_requests()  # Required for testing

        response = self._completions_create(
            messages=messages,
            model_settings=cast(dict[str, Any], model_settings or {}),
        )
        result = OpenAIStreamedResponse(
            _model_name=self._model_name,
            _response=response,
            _timestamp=datetime.now(UTC),
        )
        yield result

    async def _completions_create(
        self,
        messages: list[ModelMessage],
        model_settings: dict[str, Any],
    ) -> AsyncIterable[ChatCompletionChunk]:
        q = self.beaker_client.queue.get(self._model_name)

        new_messages = beaker_queues_map_pydantic_messages_to_dict(messages)

        queue_input = {
            "model": q.id,
            "messages": new_messages,
            "stream": True,
            **model_settings,
        }

        entry = self.beaker_client.queue.create_entry(q, input=queue_input, expires_in_sec=EXPIRES_IN)

        index = 0
        for resp in entry:
            if resp.HasField("pending_entry"):
                # TODO: handle this
                continue
            elif resp.HasField("result"):
                result = json_format.MessageToDict(resp.result)
                yield ChatCompletionChunk(
                    id=result["id"],
                    choices=result["choices"],
                    created=result["created"],
                    model=result["model"],
                    object=result["object"],
                )
                index += 1
            elif resp.HasField("finalized_entry"):
                # TODO: maybe handle this?
                continue

    async def _process_streamed_response(self, response: AsyncIterable[ChatCompletionChunk]) -> OpenAIStreamedResponse:
        return OpenAIStreamedResponse(
            _model_name=self._model_name,
            _response=response,
            _timestamp=datetime.now(UTC),
        )

    # from openai, could be useful?
    #
    # def _get_tools(self, model_request_parameters: ModelRequestParameters) -> list[responses.FunctionToolParam]:
    #     tools = [self._map_tool_definition(r) for r in model_request_parameters.function_tools]
    #     if model_request_parameters.output_tools:
    #         tools += [self._map_tool_definition(r) for r in model_request_parameters.output_tools]
    #     return tools

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def system(self) -> str:
        return self._system

def beaker_queues_map_pydantic_messages_to_dict(model_messages: list[ModelMessage]) -> list[dict]:
    messages: list[dict] = []
    for msg in model_messages:
        match msg:
            case ModelRequest():
                for part in msg.parts:
                    match part:
                        case UserPromptPart():
                            content = "".join(c for c in part.content if isinstance(c, str))
                            file_urls = [c.url for c in part.content if isinstance(c, ImageUrl)]
                            messages.append({"role": "user", "content": content, "file_urls": file_urls})
                        case SystemPromptPart():
                            messages.append({"role": "system", "content": part.content})
            case ModelResponse():
                content = "".join(part.content for part in msg.parts if isinstance(part, TextPart))
                messages.append({"role": "assistant", "content": content})

    return messages
