from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from pydantic_ai import AgentRunResultEvent, UnexpectedModelBehavior
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

from api.thread.chat.chat_types import ChatStreamOutput
from api.thread.chat.format_output import format_event
from api.thread.chat.playground_ui_adapter._util import Event, RunInput
from core.message.message_chunk import (
    ErrorChunk,
    ErrorCode,
    ModelResponseChunk,
    StreamEndChunk,
    StreamStartChunk,
    ThinkingChunk,
    ToolCallChunk,
)
from core.message.role import Role
from db.models.message import Message, create_message_id

__all__ = ["PlaygroundUIEventStream"]

JSONL_CONTENT_TYPE = "application/jsonl"


@dataclass
class PlaygroundUIEventStream(
    UIEventStream[
        RunInput,
        Event,
        AgentDepsT,
        OutputDataT,
    ]
):
    message_id: str = field(default_factory=create_message_id)
    _step_started: bool = False

    def new_message_id(self) -> str:
        self.message_id = create_message_id()
        return self.message_id

    @property
    def content_type(self) -> str:
        return JSONL_CONTENT_TYPE

    def encode_event(self, event: ChatStreamOutput) -> str:  # noqa: PLR6301
        return format_event(event)

    async def before_stream(self) -> AsyncIterator[ChatStreamOutput]:
        yield StreamStartChunk(message=self.message_id)
        for message in self.run_input.new_messages:
            yield message

    async def before_response(self) -> AsyncIterator[ChatStreamOutput]:  # noqa: PLR6301
        return
        # we don't want to yield anything but still want the type to be right so we return then yield
        yield

    async def after_stream(self) -> AsyncIterator[ChatStreamOutput]:
        yield StreamEndChunk(message=self.message_id)

    async def handle_text_start(self, part: TextPart, follows_text: bool = False) -> AsyncIterator[ChatStreamOutput]:
        message_id = self.message_id if follows_text else self.new_message_id()

        yield ModelResponseChunk(message=message_id, content=part.content)

    async def handle_text_delta(self, delta: TextPartDelta) -> AsyncIterator[ChatStreamOutput]:
        if delta.content_delta:  # pragma: no branch
            yield ModelResponseChunk(message=self.message_id, content=delta.content_delta)

    async def handle_thinking_start(
        self,
        part: ThinkingPart,
        follows_thinking: bool = False,  # noqa: ARG002, FBT001, FBT002
    ) -> AsyncIterator[ChatStreamOutput]:
        message_id = self.new_message_id()
        if part.content:
            yield ThinkingChunk(message=message_id, content=part.content)

    async def handle_thinking_delta(self, delta: ThinkingPartDelta) -> AsyncIterator[ChatStreamOutput]:
        if delta.content_delta:
            yield ThinkingChunk(message=self.message_id, content=delta.content_delta)

    async def handle_tool_call_start(self, part: ToolCallPart | BuiltinToolCallPart) -> AsyncIterator[ChatStreamOutput]:
        yield ToolCallChunk(
            message=self.message_id,
            tool_call_id=part.tool_call_id,
            tool_name=part.tool_name,
            args=part.args,
            tool_source=None,
        )

    async def handle_tool_call_delta(self, delta: ToolCallPartDelta) -> AsyncIterator[ChatStreamOutput]:
        tool_call_id = delta.tool_call_id or ""
        assert tool_call_id, "`ToolCallPartDelta.tool_call_id` must be set"  # noqa: S101
        yield ToolCallChunk(
            message=self.message_id,
            tool_call_id=tool_call_id,
            tool_name=delta.tool_name_delta or "",
            tool_source=None,
            args=delta.args_delta,
        )

    async def handle_function_tool_result(self, event: FunctionToolResultEvent) -> AsyncIterator[ChatStreamOutput]:  # noqa: PLR6301
        result = event.result
        if isinstance(result, RetryPromptPart):
            pass
            # yield ToolOutputErrorChunk(tool_call_id=result.tool_call_id, error_text=result.model_response())
        else:
            yield Message(content=event.content, role=Role.ToolResponse)  # type: ignore

        # ToolCallResultEvent.content may hold user parts (e.g. text, images) that Vercel AI does not currently have events for

    async def on_error(self, error: Exception) -> AsyncIterator[Event]:
        self._finish_reason = "error"
        if isinstance(error, UnexpectedModelBehavior):
            yield ErrorChunk(
                error_description=str(error), message=self.message_id, error_code=ErrorCode.TOOL_CALL_ERROR
            )

        else:
            yield ErrorChunk(error_description=str(error), message=self.message_id, error_code=ErrorCode.OTHER_ERROR)

    async def handle_run_result(self, event: AgentRunResultEvent) -> AsyncIterator[Event]:  # noqa: PLR6301
        pydantic_reason = event.result.response.finish_reason  # noqa: F841
        # if pydantic_reason:
        #     self._finish_reason = _FINISH_REASON_MAP.get(pydantic_reason, "other")

        output = event.result.output  # noqa: F841
        all_messages = event.result.all_messages()  # noqa: F841
        return
        yield
