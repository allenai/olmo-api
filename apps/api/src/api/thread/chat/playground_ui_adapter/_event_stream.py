from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import override

from opentelemetry import trace
from pydantic_ai import ModelRequestPart, ModelResponsePart, UnexpectedModelBehavior
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

from api.logging.fastapi_logger import FastAPIStructLogger
from api.thread.chat.playground_ui_adapter._util import (
    Event,
    RunInput,
    create_message_from_run_input,
    tool_source_from_name,
)
from core.message.flat_message import FlatMessage
from core.message.message_chunk import (
    AddMessageChunk,
    ErrorChunk,
    ErrorCode,
    ModelResponseChunk,
    StartThreadChunk,
    StreamStartChunk,
    ThinkingChunk,
    ToolCallChunk,
)
from core.message.role import Role
from core.object_id import ID
from core.tools.tool_source import ToolSource
from db.models.message import Message, create_message_id
from db.models.tool_call import ToolCall

__all__ = ["PlaygroundUIEventStream"]

JSONL_CONTENT_TYPE = "application/jsonl"

logger = FastAPIStructLogger()


@dataclass
class PlaygroundUIEventStream(
    UIEventStream[
        RunInput,
        Event,
        AgentDepsT,
        OutputDataT,
    ]
):
    message_id: ID = field(default_factory=create_message_id)

    _message_ids: list[ID] = field(default_factory=list)
    message_map: dict[ID, Message] = field(default_factory=dict)
    message_part_map: dict[ID, ModelResponsePart | ModelRequestPart] = field(default_factory=dict)

    @property
    def parent_message_id(self) -> ID:
        if len(self._message_ids) > 1:
            # This accounts for the latest message in the message IDs list being the current message's ID
            return self._message_ids[-2]

        return self.run_input.parent_message_id

    def _has_message_been_sent(self, message_id: ID) -> bool:
        """
        Checks to see if a message has already been sent as a full Message.

        The UI needs to receive a Message before receiving updates so it can properly update its state. This method and the message_map help manage that state to ensure we only send one Message for each user/assistant message. The before_request and before_response events don't _quite_ map correctly to what we need.
        """
        return self.message_map.get(message_id) is not None

    def _get_add_message_chunk(self, id: ID, message: Message):
        self.message_map[id] = message
        return AddMessageChunk(message=id, id=id, messages=FlatMessage.from_message_with_children(message))

    @override
    def new_message_id(self) -> str:
        self.message_id = create_message_id()
        self._message_ids.append(self.message_id)
        return self.message_id

    def _create_message_with_defaults(
        self,
        *,
        content: str,
        role: Role,
        tool_calls: list[ToolCall] | None = None,
        thinking: str | None = None,
    ) -> Message:
        return create_message_from_run_input(
            run_input=self.run_input,
            id=self.message_id,
            content=content,
            parent=self.parent_message_id,
            tool_calls=tool_calls,
            role=role,
            thinking=thinking,
        )

    @property
    def content_type(self) -> str:
        return JSONL_CONTENT_TYPE

    # HACK: This usually outputs str, we're overriding it in an incompatible manner so we get nice chunks in chat_service
    def encode_event(self, event: Event) -> Event:  # pyright: ignore[reportIncompatibleMethodOverride] # noqa: PLR6301
        return event

    async def before_stream(self) -> AsyncIterator[Event]:
        yield StreamStartChunk(message=self.run_input.root_message_id)

        messages = FlatMessage.from_message_seq(self.run_input.new_messages)
        if self.run_input.is_new_thread:
            yield StartThreadChunk(message=messages[0].id, id=messages[0].id, messages=messages)
        else:
            yield AddMessageChunk(message=messages[0].id, id=messages[0].id, messages=messages)

    async def before_request(self) -> AsyncIterator[Event]:
        self.new_message_id()
        return
        yield  # Make this an async generator

    async def before_response(self) -> AsyncIterator[Event]:
        self.new_message_id()
        return
        yield  # Make this an async generator

    @override
    async def after_stream(self) -> AsyncIterator[Event]:
        # We're intentionally not emitting an event here so the caller can handle the final events. The caller is responsible for emitting end chunks
        return
        yield  # Make this an async generator

    async def handle_text_start(self, part: TextPart, follows_text: bool = False) -> AsyncIterator[Event]:  # noqa: ARG002, FBT001, FBT002
        if self._has_message_been_sent(self.message_id):
            yield ModelResponseChunk(message=self.message_id, content=part.content)
            part.id = self.message_id
            self.message_part_map[self.message_id] = part
        else:
            message = self._create_message_with_defaults(content=part.content, role=Role.Assistant)
            yield self._get_add_message_chunk(message.id, message)
            part.id = message.id
            self.message_part_map[message.id] = part

    async def handle_text_delta(self, delta: TextPartDelta) -> AsyncIterator[Event]:
        if delta.content_delta:
            yield ModelResponseChunk(message=self.message_id, content=delta.content_delta)

    async def handle_thinking_start(
        self,
        part: ThinkingPart,
        follows_thinking: bool = False,  # noqa: ARG002, FBT001, FBT002
    ) -> AsyncIterator[Event]:
        if self._has_message_been_sent(self.message_id):
            yield ThinkingChunk(message=self.message_id, content=part.content)
            part.id = self.message_id
        else:
            message = self._create_message_with_defaults(content="", role=Role.Assistant, thinking=part.content)
            yield self._get_add_message_chunk(message.id, message)
            part.id = message.id

    async def handle_thinking_delta(self, delta: ThinkingPartDelta) -> AsyncIterator[Event]:
        if delta.content_delta:
            yield ThinkingChunk(message=self.message_id, content=delta.content_delta)

    async def handle_tool_call_start(self, part: ToolCallPart | BuiltinToolCallPart) -> AsyncIterator[Event]:
        if not self._has_message_been_sent(self.message_id):
            message = self._create_message_with_defaults(content="", role=Role.Assistant)
            yield self._get_add_message_chunk(message.id, message)

        tool_source = tool_source_from_name(tool_name=part.tool_name, user_tool_names=self.run_input.user_tool_names)

        yield ToolCallChunk(
            message=self.message_id,
            tool_call_id=part.tool_call_id,
            tool_name=part.tool_name,
            args=part.args,
            tool_source=tool_source,
        )
        part.id = self.message_id

    async def handle_tool_call_delta(self, delta: ToolCallPartDelta) -> AsyncIterator[Event]:
        tool_call_id = delta.tool_call_id or ""
        assert tool_call_id, "`ToolCallPartDelta.tool_call_id` must be set"  # noqa: S101

        yield ToolCallChunk(
            message=self.message_id,
            tool_call_id=tool_call_id,
            tool_name=delta.tool_name_delta or "",
            tool_source=None,
            args=delta.args_delta,
        )

    async def handle_function_tool_result(self, event: FunctionToolResultEvent) -> AsyncIterator[Event]:
        if self._has_message_been_sent(self.message_id):
            # Pydantic doesn't call before_response before each function tool. Since we need them in separate messages we need to make a new ID if we've already sent a message for this message_id
            self.new_message_id()

        result = event.result
        if isinstance(result, RetryPromptPart):
            yield ErrorChunk(
                message=self.message_id,
                error_code=ErrorCode.TOOL_CALL_ERROR,
                error_description=result.model_response(),
            )
        else:
            tool_calls = [
                ToolCall(
                    tool_call_id=result.tool_call_id,
                    tool_name=result.tool_name,
                    tool_source=ToolSource.MCP,
                    args=result.model_response_object(),
                    message_id=self.message_id,
                )
            ]

            message = self._create_message_with_defaults(
                content=result.model_response_str(),
                role=Role.ToolResponse,
                tool_calls=tool_calls,
            )

            yield self._get_add_message_chunk(message.id, message)
            result.metadata = {"message_id": message.id}

    async def on_error(self, error: Exception) -> AsyncIterator[Event]:
        self._finish_reason = "error"

        logger.exception("inference.stream-error")
        span = trace.get_current_span()
        span.set_status(trace.StatusCode.ERROR)
        span.record_exception(error)
        span.add_event("inference.stream-error")

        if isinstance(error, UnexpectedModelBehavior):
            yield ErrorChunk(
                error_description=error.message, message=self.message_id, error_code=ErrorCode.TOOL_CALL_ERROR
            )

        else:
            yield ErrorChunk(error_description=str(error), message=self.message_id, error_code=ErrorCode.OTHER_ERROR)
