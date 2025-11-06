from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property

from pydantic_ai.messages import (
    ModelMessage,
)
from pydantic_ai.output import OutputDataT
from pydantic_ai.tools import AgentDepsT
from pydantic_ai.ui import UIAdapter, UIEventStream
from src.dao.engine_models.message import Message
from src.pydantic_inference.pydantic_ai_helpers import pydantic_map_messages

from ._event_stream import PlaygroundUIEventStream
from ._util import StreamReturnType

__all__ = ["PlaygroundUIAdapter"]


@dataclass
class PlaygroundUIAdapter(UIAdapter[list[Message], Message, StreamReturnType, AgentDepsT, OutputDataT]):
    def build_run_input(cls, body: bytes) -> list[Message]:  # type: ignore # noqa: N805
        raise NotImplementedError

    def build_event_stream(
        self,
    ) -> UIEventStream[list[Message], StreamReturnType, AgentDepsT, OutputDataT]:
        return PlaygroundUIEventStream(self.run_input, accept=self.accept)

    @cached_property
    def messages(self) -> list[ModelMessage]:
        return self.load_messages(self.run_input)

    @classmethod
    def load_messages(cls, messages: Sequence[Message]) -> list[ModelMessage]:
        return pydantic_map_messages(messages, None)
