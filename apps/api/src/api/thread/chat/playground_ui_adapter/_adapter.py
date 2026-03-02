from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from mimetypes import guess_type

from fastapi import UploadFile
from fastapi_problem.error import ServerProblem, UnprocessableProblem
from pydantic_ai import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    MultiModalContent,
    VideoUrl,
)
from pydantic_ai.messages import (
    ModelMessage,
)
from pydantic_ai.output import OutputDataT
from pydantic_ai.tools import AgentDepsT
from pydantic_ai.ui import UIAdapter, UIEventStream

from api.thread.chat.mapping import map_messages_to_pydantic_ai_format
from db.models.message import Message

from ._event_stream import PlaygroundUIEventStream
from ._util import Event, RunInput, UIMessage

__all__ = ["PlaygroundUIAdapter"]


class UnsupportedMediaTypeError(UnprocessableProblem): ...


def _map_part_from_file(file: str | UploadFile) -> MultiModalContent:
    match file:
        case UploadFile():
            return BinaryContent(data=file.file.read(), media_type=file.content_type or "")

    (mimetype, _encoding) = guess_type(file)

    match mimetype:
        case None:
            # Defaulting to Image for now since most of our uploads are images
            # We can error if we enforce file extensions on upload
            return ImageUrl(file)  # pyright: ignore[reportCallIssue]

        case mimetype if mimetype.startswith("video"):
            return VideoUrl(file)  # pyright: ignore[reportCallIssue]

        case mimetype if mimetype.startswith("image"):
            return ImageUrl(file)  # pyright: ignore[reportCallIssue]

        case mimetype if mimetype.startswith(("text", "application")):
            return DocumentUrl(file)  # pyright: ignore[reportCallIssue]

        case mimetype if mimetype.startswith("audio"):
            return AudioUrl(file)  # pyright: ignore[reportCallIssue]

    unsupported_media_type_msg = f"File URL {file} has unsupported MIME type {mimetype}"
    raise UnsupportedMediaTypeError(unsupported_media_type_msg)


class InvalidToolResponseError(ServerProblem): ...


@dataclass
class PlaygroundUIAdapter(UIAdapter[RunInput, UIMessage, Event, AgentDepsT, OutputDataT]):
    def build_run_input(cls, body: bytes) -> list[Message]:  # type: ignore # noqa: N805
        raise NotImplementedError

    def build_event_stream(
        self,
    ) -> UIEventStream[RunInput, Event, AgentDepsT, OutputDataT]:
        return PlaygroundUIEventStream(self.run_input, accept=self.accept)

    @cached_property
    def messages(self) -> list[ModelMessage]:
        return self.load_messages(self.run_input.all_messages)

    @classmethod
    def load_messages(cls, messages: Sequence[UIMessage]) -> list[ModelMessage]:
        agent_messages = map_messages_to_pydantic_ai_format(messages)

        return agent_messages
