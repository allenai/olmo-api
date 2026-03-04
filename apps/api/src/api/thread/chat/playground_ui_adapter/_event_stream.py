from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from opentelemetry import trace
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

from api.logging.fastapi_logger import FastAPIStructLogger
from api.thread.chat.chat_types import ChatStreamOutput
from api.thread.chat.format_output import format_event
from api.thread.chat.playground_ui_adapter._util import (
    Event,
    RunInput,
    create_message_from_run_input,
    map_response_pydantic_messages_to_messages,
    map_tool_call_part_to_tool_call,
)
from core.message.flat_message import FlatMessage
from core.message.message_chunk import (
    AddMessageChunk,
    ErrorChunk,
    ErrorCode,
    FinalThreadChunk,
    ModelResponseChunk,
    StartThreadChunk,
    StreamEndChunk,
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
    _message_ids: list[ID] = field(default_factory=list)
    parent_message_id: ID = field(default_factory=create_message_id)
    message_id: ID = field(default_factory=create_message_id)
    message_map: dict[ID, Message] = field(default_factory=dict)

    def _has_message_been_sent(self, message_id: ID) -> bool:
        """
        Checks to see if a message has already been sent as a full Message.

        The UI needs to receive a Message before receiving updates so it can properly update its state. This method and the message_map help manage that state to ensure we only send one Message for each user/assistant message.
        """
        return self.message_map.get(message_id) is not None

    def new_message_id(self) -> str:
        self.parent_message_id = self.message_id
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

    def encode_event(self, event: ChatStreamOutput) -> str:  # noqa: PLR6301
        return format_event(event)

    async def before_stream(self) -> AsyncIterator[ChatStreamOutput]:
        yield StreamStartChunk(message=self.run_input.root_message_id)
        messages = FlatMessage.from_message_seq(self.run_input.new_messages)
        if self.run_input.is_new_thread:
            yield StartThreadChunk(message=messages[0].id, id=messages[0].id, messages=messages)
        else:
            yield AddMessageChunk(message=messages[0].id, id=messages[0].id, messages=messages)

    async def before_request(self) -> AsyncIterator[ChatStreamOutput]:
        self.new_message_id()
        return
        # we don't want to yield anything but still want the type to be right so we return then yield
        yield

    async def before_response(self) -> AsyncIterator[ChatStreamOutput]:
        self.new_message_id()
        return
        # we don't want to yield anything but still want the type to be right so we return then yield
        yield

    async def after_stream(self) -> AsyncIterator[ChatStreamOutput]:
        yield StreamEndChunk(message=self.message_id)

    async def handle_text_start(self, part: TextPart, follows_text: bool = False) -> AsyncIterator[ChatStreamOutput]:  # noqa: ARG002, FBT001, FBT002
        if self._has_message_been_sent(self.message_id):
            yield ModelResponseChunk(message=self.message_id, content=part.content)
        else:
            message = self._create_message_with_defaults(content=part.content, role=Role.Assistant)
            yield AddMessageChunk(message=message.id, id=message.id, messages=[FlatMessage.from_message(message)])

    async def handle_text_delta(self, delta: TextPartDelta) -> AsyncIterator[ChatStreamOutput]:
        if delta.content_delta:
            yield ModelResponseChunk(message=self.message_id, content=delta.content_delta)

    async def handle_thinking_start(
        self,
        part: ThinkingPart,
        follows_thinking: bool = False,  # noqa: ARG002, FBT001, FBT002
    ) -> AsyncIterator[ChatStreamOutput]:
        if self._has_message_been_sent(self.message_id):
            yield ThinkingChunk(message=self.message_id, content=part.content)
        else:
            message = self._create_message_with_defaults(content="", role=Role.Assistant, thinking=part.content)
            yield AddMessageChunk(message=message.id, id=message.id, messages=[FlatMessage.from_message(message)])

    async def handle_thinking_delta(self, delta: ThinkingPartDelta) -> AsyncIterator[ChatStreamOutput]:
        if delta.content_delta:
            yield ThinkingChunk(message=self.message_id, content=delta.content_delta)

    async def handle_tool_call_start(self, part: ToolCallPart | BuiltinToolCallPart) -> AsyncIterator[ChatStreamOutput]:
        if self._has_message_been_sent(self.message_id):
            yield ToolCallChunk(
                message=self.message_id,
                tool_call_id=part.tool_call_id,
                tool_name=part.tool_name,
                args=part.args,
                tool_source=None,
            )
        else:
            tool_call = map_tool_call_part_to_tool_call(
                part, self.message_id, user_tool_names=self.run_input.user_tool_names
            )
            message = self._create_message_with_defaults(content="", role=Role.Assistant, tool_calls=[tool_call])
            yield AddMessageChunk(message=message.id, id=message.id, messages=[FlatMessage.from_message(message)])

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

    async def handle_function_tool_result(self, event: FunctionToolResultEvent) -> AsyncIterator[ChatStreamOutput]:
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

            flat_message = FlatMessage.from_message(message)

            yield AddMessageChunk(message=message.id, id=message.id, messages=[flat_message])

    async def on_error(self, error: Exception) -> AsyncIterator[Event]:
        self._finish_reason = "error"

        logger.exception("inference.stream-error")
        span = trace.get_current_span()
        span.set_status(trace.StatusCode.ERROR)
        span.record_exception(error)

        if isinstance(error, UnexpectedModelBehavior):
            yield ErrorChunk(
                error_description=str(error), message=self.message_id, error_code=ErrorCode.TOOL_CALL_ERROR
            )

        else:
            yield ErrorChunk(error_description=str(error), message=self.message_id, error_code=ErrorCode.OTHER_ERROR)

    async def handle_run_result(self, event: AgentRunResultEvent) -> AsyncIterator[Event]:
        try:
            pydantic_reason = event.result.response.finish_reason  # noqa: F841
            # if pydantic_reason:
            #     self._finish_reason = _FINISH_REASON_MAP.get(pydantic_reason, "other")

            new_messages = event.result.new_messages()

            mapped_new_messages = map_response_pydantic_messages_to_messages(
                new_messages, message_ids=self._message_ids, run_input=self.run_input
            )

            first_new_message = await self.run_input.handle_final_messages([
                *self.run_input.new_messages,
                *mapped_new_messages,
            ])

            messages = FlatMessage.from_message_with_children(first_new_message)

            yield FinalThreadChunk(message=messages[0].id, id=messages[0].id, messages=messages)
        except Exception as e:  # noqa: BLE001
            async for error_event in self.on_error(e):
                yield error_event
