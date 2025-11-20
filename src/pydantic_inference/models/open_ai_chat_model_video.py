import base64
from collections.abc import AsyncIterable, AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Required, assert_never, cast

from openai import AsyncStream
from openai.types import chat, responses
from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartInputAudioParam,
    ChatCompletionContentPartParam,
    ChatCompletionContentPartTextParam,
)
from openai.types.chat.chat_completion_content_part_image_param import ImageURL
from openai.types.chat.chat_completion_content_part_input_audio_param import InputAudio
from openai.types.chat.chat_completion_content_part_param import File, FileFile
from typing_extensions import TypedDict

from pydantic_ai import ModelProfile, RunContext, UnexpectedModelBehavior, _utils, usage
from pydantic_ai.messages import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    FinishReason,
    ImageUrl,
    ModelMessage,
    ModelResponse,
    ModelResponseStreamEvent,
    PartStartEvent,
    ThinkingPart,
    UserPromptPart,
    VideoUrl,
)
from pydantic_ai.models import (
    ModelRequestParameters,
    StreamedResponse,
    check_allow_model_requests,
    download_item,
)
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.settings import ModelSettings

_CHAT_FINISH_REASON_MAP: dict[
    Literal["stop", "length", "tool_calls", "content_filter", "function_call"], FinishReason
] = {
    "stop": "stop",
    "length": "length",
    "tool_calls": "tool_call",
    "content_filter": "content_filter",
    "function_call": "tool_call",
}


def _map_usage(response: chat.ChatCompletion | ChatCompletionChunk | responses.Response) -> usage.RequestUsage:
    response_usage = response.usage
    if response_usage is None:
        return usage.RequestUsage()
    if isinstance(response_usage, responses.ResponseUsage):
        details: dict[str, int] = {
            key: value
            for key, value in response_usage.model_dump(
                exclude={"input_tokens", "output_tokens", "total_tokens"}
            ).items()
            if isinstance(value, int)
        }
        # Handle vLLM compatibility - some providers don't include token details
        if getattr(response_usage, "input_tokens_details", None) is not None:
            cache_read_tokens = response_usage.input_tokens_details.cached_tokens
        else:
            cache_read_tokens = 0

        if getattr(response_usage, "output_tokens_details", None) is not None:
            details["reasoning_tokens"] = response_usage.output_tokens_details.reasoning_tokens
        else:
            details["reasoning_tokens"] = 0

        return usage.RequestUsage(
            input_tokens=response_usage.input_tokens,
            output_tokens=response_usage.output_tokens,
            cache_read_tokens=cache_read_tokens,
            details=details,
        )
    details = {
        key: value
        for key, value in response_usage.model_dump(
            exclude_none=True, exclude={"prompt_tokens", "completion_tokens", "total_tokens"}
        ).items()
        if isinstance(value, int)
    }
    u = usage.RequestUsage(
        input_tokens=response_usage.prompt_tokens,
        output_tokens=response_usage.completion_tokens,
        details=details,
    )
    if response_usage.completion_tokens_details is not None:
        details.update(response_usage.completion_tokens_details.model_dump(exclude_none=True))
        u.output_audio_tokens = response_usage.completion_tokens_details.audio_tokens or 0
    if response_usage.prompt_tokens_details is not None:
        u.input_audio_tokens = response_usage.prompt_tokens_details.audio_tokens or 0
        u.cache_read_tokens = response_usage.prompt_tokens_details.cached_tokens or 0
    return u


@dataclass
class OpenAIStreamedResponse(StreamedResponse):
    """Implementation of `StreamedResponse` for OpenAI models."""

    _model_name: str
    _model_profile: ModelProfile
    _response: AsyncIterable[ChatCompletionChunk]
    _timestamp: datetime
    _provider_name: str

    async def _get_event_iterator(self) -> AsyncIterator[ModelResponseStreamEvent]:
        async for chunk in self._response:
            self._usage += _map_usage(chunk)

            if chunk.id:  # pragma: no branch
                self.provider_response_id = chunk.id

            if chunk.model:
                self._model_name = chunk.model

            try:
                choice = chunk.choices[0]
            except IndexError:
                continue

            # When using Azure OpenAI and an async content filter is enabled, the openai SDK can return None deltas.
            if choice.delta is None:  # pyright: ignore[reportUnnecessaryComparison]
                continue

            if raw_finish_reason := choice.finish_reason:
                self.provider_details = {"finish_reason": raw_finish_reason}
                self.finish_reason = _CHAT_FINISH_REASON_MAP.get(raw_finish_reason)

            # Handle the text part of the response
            content = choice.delta.content
            if content is not None:
                maybe_event = self._parts_manager.handle_text_delta(
                    vendor_part_id="content",
                    content=content,
                    thinking_tags=self._model_profile.thinking_tags,
                    ignore_leading_whitespace=self._model_profile.ignore_streamed_leading_whitespace,
                )
                if maybe_event is not None:  # pragma: no branch
                    if isinstance(maybe_event, PartStartEvent) and isinstance(maybe_event.part, ThinkingPart):
                        maybe_event.part.id = "content"
                        maybe_event.part.provider_name = self.provider_name
                    yield maybe_event

            reasoning_content = getattr(choice.delta, "reasoning_content", None)
            reasoning = getattr(choice.delta, "reasoning", None)
            # The `reasoning_content` field is only present in DeepSeek models.
            # https://api-docs.deepseek.com/guides/reasoning_model
            if reasoning_content and not reasoning:
                yield self._parts_manager.handle_thinking_delta(
                    vendor_part_id="reasoning_content",
                    id="reasoning_content",
                    content=reasoning_content,
                    provider_name=self.provider_name,
                )

            # The `reasoning` field is only present in gpt-oss via Ollama and OpenRouter.
            # - https://cookbook.openai.com/articles/gpt-oss/handle-raw-cot#chat-completions-api
            # - https://openrouter.ai/docs/use-cases/reasoning-tokens#basic-usage-with-reasoning-tokens
            elif reasoning:  # pragma: no cover
                yield self._parts_manager.handle_thinking_delta(
                    vendor_part_id="reasoning",
                    id="reasoning",
                    content=reasoning,
                    provider_name=self.provider_name,
                )

            for dtc in choice.delta.tool_calls or []:
                maybe_event = self._parts_manager.handle_tool_call_delta(
                    vendor_part_id=dtc.index,
                    tool_name=dtc.function and dtc.function.name,
                    args=dtc.function and dtc.function.arguments,
                    tool_call_id=dtc.id,
                )
                if maybe_event is not None:
                    yield maybe_event

    @property
    def model_name(self) -> str:
        """Get the model name of the response."""
        return self._model_name

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return self._provider_name

    @property
    def timestamp(self) -> datetime:
        """Get the timestamp of the response."""
        return self._timestamp


class OpenAIChatModelVideo(OpenAIChatModel):
    async def _map_user_prompt(self, part: UserPromptPart) -> chat.ChatCompletionUserMessageParam:
        content: str | list[ChatCompletionContentPartParam | ChatCompletionContentPartVideoParam]
        if isinstance(part.content, str):
            content = part.content
        else:
            content = []
            for item in part.content:
                if isinstance(item, str):
                    content.append(ChatCompletionContentPartTextParam(text=item, type="text"))
                elif isinstance(item, ImageUrl):
                    image_url: ImageURL = {"url": item.url}
                    if metadata := item.vendor_metadata:
                        image_url["detail"] = metadata.get("detail", "auto")
                    if item.force_download:
                        image_content = await download_item(item, data_format="base64_uri", type_format="extension")
                        image_url["url"] = image_content["data"]
                    content.append(ChatCompletionContentPartImageParam(image_url=image_url, type="image_url"))
                elif isinstance(item, BinaryContent):
                    if self._is_text_like_media_type(item.media_type):
                        # Inline text-like binary content as a text block
                        content.append(
                            self._inline_text_file_part(
                                item.data.decode("utf-8"),
                                media_type=item.media_type,
                                identifier=item.identifier,
                            )
                        )
                    elif item.is_image:
                        image_url = ImageURL(url=item.data_uri)
                        if metadata := item.vendor_metadata:
                            image_url["detail"] = metadata.get("detail", "auto")
                        content.append(ChatCompletionContentPartImageParam(image_url=image_url, type="image_url"))
                    elif item.is_audio:
                        assert item.format in ("wav", "mp3")
                        audio = InputAudio(data=base64.b64encode(item.data).decode("utf-8"), format=item.format)  # type:ignore
                        content.append(ChatCompletionContentPartInputAudioParam(input_audio=audio, type="input_audio"))
                    elif item.is_document:
                        content.append(
                            File(
                                file=FileFile(
                                    file_data=item.data_uri,
                                    filename=f"filename.{item.format}",
                                ),
                                type="file",
                            )
                        )
                    elif item.is_video:
                        # Updated by Ai2 to handle VideoUrl
                        video_url = VideoURL(url=item.data_uri)
                        content.append(ChatCompletionContentPartVideoParam(video_url=video_url, type="video_url"))
                    else:  # pragma: no cover
                        raise RuntimeError(f"Unsupported binary content type: {item.media_type}")
                elif isinstance(item, AudioUrl):
                    downloaded_item = await download_item(item, data_format="base64", type_format="extension")
                    assert downloaded_item["data_type"] in (
                        "wav",
                        "mp3",
                    ), f"Unsupported audio format: {downloaded_item['data_type']}"
                    audio = InputAudio(data=downloaded_item["data"], format=downloaded_item["data_type"])  # type:ignore
                    content.append(ChatCompletionContentPartInputAudioParam(input_audio=audio, type="input_audio"))
                elif isinstance(item, DocumentUrl):
                    if self._is_text_like_media_type(item.media_type):
                        downloaded_text = await download_item(item, data_format="text")
                        content.append(
                            self._inline_text_file_part(
                                downloaded_text["data"],
                                media_type=item.media_type,
                                identifier=item.identifier,
                            )
                        )
                    else:
                        downloaded_item = await download_item(item, data_format="base64_uri", type_format="extension")
                        content.append(
                            File(
                                file=FileFile(
                                    file_data=downloaded_item["data"],
                                    filename=f"filename.{downloaded_item['data_type']}",
                                ),
                                type="file",
                            )
                        )
                elif isinstance(item, VideoUrl):
                    # Updated by Ai2 to handle VideoUrl
                    video_url = VideoURL(url=item.url)
                    content.append(ChatCompletionContentPartVideoParam(video_url=video_url, type="video_url"))
                else:
                    assert_never(item)
        return chat.ChatCompletionUserMessageParam(role="user", content=content)  # type:ignore

    async def _process_streamed_response(  # type: ignore[override]
        self, response: AsyncStream[ChatCompletionChunk], model_request_parameters: ModelRequestParameters
    ) -> OpenAIStreamedResponse:
        """Process a streamed response, and prepare a streaming response to return."""
        peekable_response = _utils.PeekableAsyncStream(response)
        first_chunk = await peekable_response.peek()
        if isinstance(first_chunk, _utils.Unset):
            raise UnexpectedModelBehavior(  # pragma: no cover
                "Streamed response ended without content or tool calls"
            )

        # When using Azure OpenAI and a content filter is enabled, the first chunk will contain a `''` model name,
        # so we set it from a later chunk in `OpenAIChatStreamedResponse`.
        model_name = first_chunk.model or self._model_name

        return OpenAIStreamedResponse(
            model_request_parameters=model_request_parameters,
            _model_name=model_name,
            _model_profile=self.profile,
            _response=peekable_response,
            _timestamp=_utils.number_to_datetime(first_chunk.created),
            _provider_name=self._provider.name,
        )

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncIterator[StreamedResponse]:
        check_allow_model_requests()
        model_settings, model_request_parameters = self.prepare_request(
            model_settings,
            model_request_parameters,
        )
        response = await self._completions_create(
            messages, True, cast(OpenAIChatModelSettings, model_settings or {}), model_request_parameters
        )
        async with response:
            yield await self._process_streamed_response(response, model_request_parameters)

    def _process_response(self, response: chat.ChatCompletion | str) -> ModelResponse:
        if not isinstance(response, chat.ChatCompletion):
            invalid_response_msg = "Invalid response from OpenAI chat completions endpoint, expected JSON data"
            raise UnexpectedModelBehavior(invalid_response_msg)

        if response.choices:
            choice = response.choices[0]
            if getattr(choice.message, "reasoning_content", None) and getattr(choice.message, "reasoning", None):
                setattr(choice.message, "reasoning_content", None)  # noqa: B010

        return super()._process_response(response)


class VideoURL(TypedDict, total=False):
    url: Required[str]
    """Either a URL of the image or the base64 encoded image data."""


class ChatCompletionContentPartVideoParam(TypedDict, total=False):
    video_url: Required[VideoURL]

    type: Required[Literal["video_url"]]
    """The type of the content part."""
