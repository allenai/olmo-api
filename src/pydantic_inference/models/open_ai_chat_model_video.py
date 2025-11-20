import base64
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal, Required, assert_never, cast

from openai.types import chat
from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartInputAudioParam,
    ChatCompletionContentPartParam,
    ChatCompletionContentPartTextParam,
)
from openai.types.chat.chat_completion_content_part_image_param import ImageURL
from openai.types.chat.chat_completion_content_part_input_audio_param import InputAudio
from openai.types.chat.chat_completion_content_part_param import File, FileFile
from typing_extensions import TypedDict

from pydantic_ai import RunContext, UnexpectedModelBehavior
from pydantic_ai.messages import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    ModelMessage,
    ModelResponse,
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

    # async def request(
    #     self,
    #     messages: list[ModelMessage],
    #     model_settings: ModelSettings | None,
    #     model_request_parameters: ModelRequestParameters,
    # ) -> ModelResponse:
    #     model_settings, model_request_parameters = self.prepare_request(
    #         model_settings,
    #         model_request_parameters,
    #     )
    #     response = await self._completions_create(
    #         messages, False, cast(OpenAIChatModelSettings, model_settings or {}), model_request_parameters
    #     )
    #     model_response = self._process_response(response)
    #     return model_response

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
