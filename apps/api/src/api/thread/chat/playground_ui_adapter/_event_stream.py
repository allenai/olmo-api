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
from api.thread.chat.util import attach_message_children
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
from core.object_id import ID
from core.tools.tool_source import ToolSource
from db.models.message import Message, create_message_id
from db.models.tool_call import ToolCall

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
    _message_ids: list[ID] = field(default_factory=list)
    parent_message_id: ID = field(default_factory=create_message_id)
    message_id: ID = field(default_factory=create_message_id)

    tool_call_message_map: dict[str, Message] = field(default_factory=dict)
    new_messages: list[Message] = field(default_factory=list)

    def new_message_id(self) -> str:
        self.parent_message_id = self.message_id
        self.message_id = create_message_id()
        self._message_ids.append(self.message_id)
        return self.message_id

    @property
    def content_type(self) -> str:
        return JSONL_CONTENT_TYPE

    def encode_event(self, event: ChatStreamOutput) -> str:  # noqa: PLR6301
        return format_event(event)

    async def before_stream(self) -> AsyncIterator[ChatStreamOutput]:
        yield StreamStartChunk(message=self.message_id)
        message_with_children = attach_message_children(self.run_input.new_messages)
        yield message_with_children[0]

    async def before_request(self) -> AsyncIterator[ChatStreamOutput]:
        self.new_message_id()
        return
        yield

    async def after_request(self) -> AsyncIterator[ChatStreamOutput]:
        return
        yield

    async def before_response(self) -> AsyncIterator[ChatStreamOutput]:
        self.new_message_id()
        return
        # we don't want to yield anything but still want the type to be right so we return then yield
        yield

    async def after_response(self) -> AsyncIterator[ChatStreamOutput]:  # noqa: PLR6301
        return
        # we don't want to yield anything but still want the type to be right so we return then yield
        yield

    async def after_stream(self) -> AsyncIterator[ChatStreamOutput]:
        yield StreamEndChunk(message=self.message_id)

    async def handle_text_start(self, part: TextPart, follows_text: bool = False) -> AsyncIterator[ChatStreamOutput]:  # noqa: ARG002, FBT001, FBT002
        yield ModelResponseChunk(message=self.message_id, content=part.content)

    async def handle_text_delta(self, delta: TextPartDelta) -> AsyncIterator[ChatStreamOutput]:
        if delta.content_delta:  # pragma: no branch
            yield ModelResponseChunk(message=self.message_id, content=delta.content_delta)

    async def handle_thinking_start(
        self,
        part: ThinkingPart,
        follows_thinking: bool = False,  # noqa: ARG002, FBT001, FBT002
    ) -> AsyncIterator[ChatStreamOutput]:
        if part.content:
            yield ThinkingChunk(message=self.message_id, content=part.content)

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

    async def handle_function_tool_result(self, event: FunctionToolResultEvent) -> AsyncIterator[ChatStreamOutput]:
        result = event.result
        if isinstance(result, RetryPromptPart):
            yield ErrorChunk(
                message=self.message_id,
                error_code=ErrorCode.TOOL_CALL_ERROR,
                error_description=result.model_response(),
            )
        else:
            message = Message(
                id=self.message_id,
                content=result.model_response_str(),
                role=Role.ToolResponse,
                creator=self.run_input.creator,
                opts=self.run_input.inference_opts,
                root=self.run_input.root_message_id,
                parent=self.parent_message_id,
                model_id=self.run_input.model_id,
                model_host=self.run_input.model_host,
                tool_calls=[
                    ToolCall(
                        tool_call_id=result.tool_call_id,
                        tool_name=result.tool_name,
                        tool_source=ToolSource.MCP,
                        args=None,
                        message_id=self.message_id,
                    )
                ],
            )

            self.tool_call_message_map.update({result.tool_call_id: message})

            yield message

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
        new_messages = event.result.new_messages()

        # Yield user message and any new messages
        return
        yield
