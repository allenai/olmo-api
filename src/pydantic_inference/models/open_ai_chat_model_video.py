import base64
from typing import Literal, Required, assert_never

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
from pydantic_ai.messages import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    UserPromptPart,
    VideoUrl,
)
from pydantic_ai.models import download_item
from pydantic_ai.models.openai import OpenAIChatModel
from typing_extensions import TypedDict


class OpenAIChatModelVideo(OpenAIChatModel):
    async def _map_user_prompt(self, part: UserPromptPart) -> chat.ChatCompletionUserMessageParam:
        content: str | list[ChatCompletionContentPartParam]
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
                        content.append(ChatCompletionContentPartVideoParam(video_url=video_url, type="video_url"))  # type:ignore
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
                    content.append(ChatCompletionContentPartVideoParam(video_url=video_url, type="video_url"))  # type:ignore
                else:
                    assert_never(item)
        return chat.ChatCompletionUserMessageParam(role="user", content=content)


class VideoURL(TypedDict, total=False):
    url: Required[str]
    """Either a URL of the image or the base64 encoded image data."""


class ChatCompletionContentPartVideoParam(TypedDict, total=False):
    video_url: Required[VideoURL]

    type: Required[Literal["video_url"]]
    """The type of the content part."""
