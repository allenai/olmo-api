import base64
from collections.abc import AsyncIterable, AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, assert_never, cast

from beaker import Beaker
from beaker.config import Config as BeakerConfig
from google.protobuf import json_format
from openai.types.chat import ChatCompletionChunk
from pydantic_ai.messages import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
    VideoUrl,
)
from pydantic_ai.models import Model, ModelRequestParameters, check_allow_model_requests
from pydantic_ai.models.openai import OpenAIStreamedResponse
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import ToolDefinition

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
    _system: str = field(default="ai2", init=False)

    def __init__(self, model: str, beaker_config: BeakerConfig | None = None) -> None:
        """Initialize the model with a beaker client."""
        if not beaker_config:
            cfg = get_config()
            beaker_config = BeakerConfig(rpc_address=cfg.beaker.address, user_token=cfg.beaker.user_token)

        self.model = model
        self._model_name = model
        self.beaker_client = Beaker(beaker_config)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def system(self) -> str:
        return self._system

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

        # tools = self._get_tools(model_request_parameters)

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

        new_messages = self._map_messages(messages)

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

    def _map_messages(self, model_messages: list[ModelMessage]) -> list[dict]:
        messages: list[dict] = []
        for msg in model_messages:
            match msg:
                case ModelRequest():
                    for part in msg.parts:
                        match part:
                            case UserPromptPart():
                                messages.append(self._map_user_prompt(part))
                            case SystemPromptPart():
                                messages.append({"role": "system", "content": part.content})
                            case ToolReturnPart():
                                # openapi guard tool_call_id, if its None, it generates a uuid based new one
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": part.tool_call_id,
                                    "content": part.model_response_str(),
                                })
                            case RetryPromptPart():
                                if part.tool_name is None:
                                    messages.append({"role": "user", "content": part.model_response()})
                                else:
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": part.tool_call_id,
                                        "content": part.model_response(),
                                    })
                            case _:
                                assert_never(part)
                case ModelResponse():
                    texts: list[str] = []
                    tool_calls: list[dict] = []
                    for item in msg.parts:
                        match item:
                            case TextPart():
                                texts.append(item.content)
                            case ThinkingPart():
                                # From OpenAIModel
                                # NOTE: We don't send ThinkingPart to the providers yet. If you are unsatisfied with this,
                                # please open an issue. The below code is the code to send thinking to the provider.
                                # texts.append(f'<think>\n{item.content}\n</think>')
                                pass
                            case ToolCallPart():
                                tool_calls.append(self._map_tool_call(item))
                            case _:
                                assert_never(item)  # pragma: no cover
                    message_param: dict[str, Any] = {"role": "assistant"}
                    if texts:
                        # From OpenAIModel
                        # Note: model responses from this model should only have one text item, so the following
                        # shouldn't merge multiple texts into one unless you switch models between runs:
                        message_param["content"] = "\n\n".join(texts)
                    if tool_calls:
                        message_param["tool_calls"] = tool_calls
                    messages.append(message_param)

        return messages

    @staticmethod
    def _map_tool_call(t: ToolCallPart) -> dict[str, Any]:
        # From OpenAIModel, may not be the right format
        return {
            "id": t.tool_call_id,
            "type": "function",
            "function": {"name": t.tool_name, "arguments": t.args_as_json_str()},
        }

    @staticmethod
    def _map_user_prompt(part: UserPromptPart) -> dict[str, Any]:
        prompt: dict[str, Any] = {
            "role": "user",
        }
        if isinstance(part.content, str):
            prompt["content"] = part.content
        elif isinstance(part.content, list):
            content = ""
            file_urls = []
            for item in part.content:
                match item:
                    case str():
                        content += item
                    case ImageUrl() | AudioUrl() | DocumentUrl() | VideoUrl():
                        file_urls.append(item.url)
                    case BinaryContent():
                        # Is this correct?
                        file_urls.append(f"data:{item.media_type};base64,{base64.b64encode(item.data).decode('utf-8')}")
                    case _:
                        assert_never(item)  # type: ignore
            if file_urls:
                prompt["file_urls"] = file_urls
            if content:
                prompt["content"] = content
        else:
            assert_never(part.content)  # type: ignore
        return prompt

    # Unused, but maybe need in future

    def _get_tools(self, model_request_parameters: ModelRequestParameters) -> list[dict[str, Any]]:
        tools = [self._map_tool_definition(r) for r in model_request_parameters.function_tools]
        if model_request_parameters.output_tools:
            tools += [self._map_tool_definition(r) for r in model_request_parameters.output_tools]
        return tools

    @staticmethod
    def _map_tool_definition(f: ToolDefinition) -> dict[str, Any]:
        tool_param = {
            "type": "function",
            "function": {
                "name": f.name,
                "description": f.description or "",
                "parameters": f.parameters_json_schema,
            },
        }
        # Needed?
        # if f.strict and OpenAIModelProfile.from_profile(self.profile).openai_supports_strict_tool_definition:
        #     tool_param['function']['strict'] = f.strict
        return tool_param  # noqa: RET504
