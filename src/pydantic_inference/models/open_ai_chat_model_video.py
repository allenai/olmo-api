import base64
from dataclasses import replace
from typing import Any, Literal, Required, assert_never

from openai.types import chat
from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartInputAudioParam,
    ChatCompletionContentPartParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionMessageCustomToolCall,
    ChatCompletionMessageFunctionToolCall,
)
from openai.types.chat.chat_completion_content_part_image_param import ImageURL
from openai.types.chat.chat_completion_content_part_input_audio_param import InputAudio
from openai.types.chat.chat_completion_content_part_param import File, FileFile
from pydantic import ValidationError
from typing_extensions import TypedDict

from pydantic_ai import UnexpectedModelBehavior, usage
from pydantic_ai import _utils as pai_utils  # noqa: PLC2701
from pydantic_ai.messages import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    ModelResponse,
    ModelResponsePart,
    ThinkingPart,
    ToolCallPart,
    UserPromptPart,
    VideoUrl,
)
from pydantic_ai.models import download_item
from pydantic_ai.models.openai import OpenAIChatModel
from src.pydantic_inference.models.util._thinking_part import split_content_into_text_and_thinking

pai_utils


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

    def _process_response(self, response: chat.ChatCompletion | str) -> ModelResponse:
        """Process a non-streamed response, and prepare a message to return."""
        # Although the OpenAI SDK claims to return a Pydantic model (`ChatCompletion`) from the chat completions function:
        # * it hasn't actually performed validation (presumably they're creating the model with `model_construct` or something?!)
        # * if the endpoint returns plain text, the return type is a string
        # Thus we validate it fully here.
        if not isinstance(response, chat.ChatCompletion):
            raise UnexpectedModelBehavior(
                message="Invalid response from OpenAI chat completions endpoint, expected JSON data"
            )

        if response.created:
            timestamp = pai_utils.number_to_datetime(response.created)
        else:
            timestamp = pai_utils.now_utc()
            response.created = int(timestamp.timestamp())

        # Workaround for local Ollama which sometimes returns a `None` finish reason.
        if response.choices and (choice := response.choices[0]) and choice.finish_reason is None:  # pyright: ignore[reportUnnecessaryComparison]
            choice.finish_reason = "stop"

        try:
            response = chat.ChatCompletion.model_validate(response.model_dump())
        except ValidationError as e:
            validation_error_msg = f"Invalid response from OpenAI chat completions endpoint: {e}"
            raise UnexpectedModelBehavior(validation_error_msg) from e

        choice = response.choices[0]
        items: list[ModelResponsePart] = []

        # The `reasoning_content` field is only present in DeepSeek models.
        # https://api-docs.deepseek.com/guides/reasoning_model
        if reasoning_content := getattr(choice.message, "reasoning_content", None):
            items.append(ThinkingPart(id="reasoning_content", content=reasoning_content, provider_name=self.system))

        # The `reasoning` field is only present in gpt-oss via Ollama and OpenRouter.
        # - https://cookbook.openai.com/articles/gpt-oss/handle-raw-cot#chat-completions-api
        # - https://openrouter.ai/docs/use-cases/reasoning-tokens#basic-usage-with-reasoning-tokens
        if reasoning := getattr(choice.message, "reasoning", None):
            items.append(ThinkingPart(id="reasoning", content=reasoning, provider_name=self.system))

        # NOTE: We don't currently handle OpenRouter `reasoning_details`:
        # - https://openrouter.ai/docs/use-cases/reasoning-tokens#preserving-reasoning-blocks
        # If you need this, please file an issue.

        vendor_details: dict[str, Any] = {}

        # Add logprobs to vendor_details if available
        if choice.logprobs is not None and choice.logprobs.content:
            # Convert logprobs to a serializable format
            vendor_details["logprobs"] = [
                {
                    "token": lp.token,
                    "bytes": lp.bytes,
                    "logprob": lp.logprob,
                    "top_logprobs": [
                        {"token": tlp.token, "bytes": tlp.bytes, "logprob": tlp.logprob} for tlp in lp.top_logprobs
                    ],
                }
                for lp in choice.logprobs.content
            ]

        if choice.message.content is not None:
            items.extend(
                (replace(part, id="content", provider_name=self.system) if isinstance(part, ThinkingPart) else part)
                for part in split_content_into_text_and_thinking(choice.message.content, self.profile.thinking_tags)
            )
        if choice.message.tool_calls is not None:
            for c in choice.message.tool_calls:
                if isinstance(c, ChatCompletionMessageFunctionToolCall):
                    part = ToolCallPart(c.function.name, c.function.arguments, tool_call_id=c.id)
                elif isinstance(c, ChatCompletionMessageCustomToolCall):  # pragma: no cover
                    # NOTE: Custom tool calls are not supported.
                    # See <https://github.com/pydantic/pydantic-ai/issues/2513> for more details.
                    raise RuntimeError("Custom tool calls are not supported")
                else:
                    assert_never(c)
                part.tool_call_id = pai_utils.guard_tool_call_id(part)
                items.append(part)

        raw_finish_reason = choice.finish_reason
        vendor_details["finish_reason"] = raw_finish_reason
        finish_reason = _CHAT_FINISH_REASON_MAP.get(raw_finish_reason)

        return ModelResponse(
            parts=items,
            usage=_map_usage(response),
            model_name=response.model,
            timestamp=timestamp,
            provider_details=vendor_details or None,
            provider_response_id=response.id,
            provider_name=self._provider.name,
            finish_reason=finish_reason,
        )


class VideoURL(TypedDict, total=False):
    url: Required[str]
    """Either a URL of the image or the base64 encoded image data."""


class ChatCompletionContentPartVideoParam(TypedDict, total=False):
    video_url: Required[VideoURL]

    type: Required[Literal["video_url"]]
    """The type of the content part."""
