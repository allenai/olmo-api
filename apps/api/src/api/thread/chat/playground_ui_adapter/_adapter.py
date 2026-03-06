from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property

from pydantic_ai.messages import (
    ModelMessage,
)
from pydantic_ai.output import OutputDataT
from pydantic_ai.tools import AgentDepsT
from pydantic_ai.ui import UIAdapter, UIEventStream

from api.thread.chat.mapping.mapping import map_messages_to_pydantic_ai_format
from db.models.message import Message

from ._event_stream import PlaygroundUIEventStream
from ._util import Event, RunInput, UIMessage

__all__ = ["PlaygroundUIAdapter"]


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
