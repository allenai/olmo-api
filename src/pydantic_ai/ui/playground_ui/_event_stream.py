from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TypeAlias

from pydantic_ai.messages import (
    BuiltinToolCallPart,
    FunctionToolResultEvent,
    RetryPromptPart,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
)
from pydantic_ai.output import OutputDataT
from pydantic_ai.tools import AgentDepsT
from pydantic_ai.ui import UIEventStream
from src import obj
from src.dao.engine_models.message import Message
from src.dao.message.message_models import MessageStreamError, Role
from src.inference.InferenceEngine import FinishReason
from src.message.create_message_request import CreateMessageRequestWithFullMessages
from src.message.format_messages_output import format_message
from src.message.message_chunk import (
    BaseChunk,
    ModelResponseChunk,
    StreamEndChunk,
    StreamStartChunk,
    ThinkingChunk,
    ToolCallChunk,
)

__all__ = ["PlaygroundUIEventStream"]

JSONL_CONTENT_TYPE = "application/jsonl"

StreamReturnType: TypeAlias = Message | MessageStreamError | BaseChunk


@dataclass
class PlaygroundUIEventStream(
    UIEventStream[
        CreateMessageRequestWithFullMessages,
        StreamReturnType,
        AgentDepsT,
        OutputDataT,
    ]
):
    _step_started: bool = False

    def new_message_id(self) -> str:
        self.message_id = obj.new_id_generator("msg")()
        return self.message_id

    @property
    def content_type(self) -> str:
        return JSONL_CONTENT_TYPE

    def encode_event(self, event: StreamReturnType) -> str:
        return format_message(event)

    async def before_stream(self) -> AsyncIterator[StreamReturnType]:
        self.new_message_id()
        yield StreamStartChunk(message=self.message_id)

    async def before_response(self) -> AsyncIterator[StreamReturnType]:
        self.new_message_id()
        return
        yield

    async def after_stream(self) -> AsyncIterator[StreamReturnType]:
        yield StreamEndChunk(message=self.message_id)

    async def on_error(self, error: Exception) -> AsyncIterator[StreamReturnType]:
        yield MessageStreamError(message=self.message_id, error=str(error), reason=FinishReason.Unknown)

    async def handle_text_start(self, part: TextPart, follows_text: bool = False) -> AsyncIterator[StreamReturnType]:
        message_id = self.message_id if follows_text else self.new_message_id()

        yield ModelResponseChunk(message=message_id, content=part.content)

    async def handle_text_delta(self, delta: TextPartDelta) -> AsyncIterator[StreamReturnType]:
        if delta.content_delta:  # pragma: no branch
            yield ModelResponseChunk(message=self.message_id, content=delta.content_delta)

    async def handle_thinking_start(
        self, part: ThinkingPart, follows_thinking: bool = False
    ) -> AsyncIterator[StreamReturnType]:
        if part.content:
            yield ThinkingChunk(message=self.message_id, content=part.content)

    async def handle_thinking_delta(self, delta: ThinkingPartDelta) -> AsyncIterator[StreamReturnType]:
        if delta.content_delta:
            yield ThinkingChunk(message=self.message_id, content=delta.content_delta)

    async def handle_tool_call_start(self, part: ToolCallPart | BuiltinToolCallPart) -> AsyncIterator[StreamReturnType]:
        yield ToolCallChunk(
            message=self.message_id,
            tool_call_id=part.tool_call_id,
            tool_name=part.tool_name,
            args=part.args,
            tool_source=None,
        )

    async def handle_tool_call_delta(self, delta: ToolCallPartDelta) -> AsyncIterator[StreamReturnType]:
        tool_call_id = delta.tool_call_id or ""
        assert tool_call_id, "`ToolCallPartDelta.tool_call_id` must be set"
        yield ToolCallChunk(
            message=self.message_id,
            tool_call_id=tool_call_id,
            tool_name=delta.tool_name_delta or "",
            tool_source=None,
            args=delta.args_delta,
        )

    async def handle_function_tool_result(self, event: FunctionToolResultEvent) -> AsyncIterator[StreamReturnType]:
        result = event.result
        if isinstance(result, RetryPromptPart):
            pass
            # yield ToolOutputErrorChunk(tool_call_id=result.tool_call_id, error_text=result.model_response())
        else:
            yield Message(content=event.content, role=Role.ToolResponse)  # type: ignore

        # ToolCallResultEvent.content may hold user parts (e.g. text, images) that Vercel AI does not currently have events for
