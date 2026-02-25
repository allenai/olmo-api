from collections.abc import AsyncGenerator, Sequence
from typing import Annotated

from fastapi import Depends
from fastapi_problem.error import UnprocessableProblem
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from pydantic_ai import (
    AbstractToolset,
    Agent,
    AgentRunResultEvent,
    CombinedToolset,
    DeferredToolRequests,
    ExternalToolset,
    FinalResultEvent,
    FunctionToolResultEvent,
    ModelMessage,
    ToolDefinition,
    UsageLimits,
)

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.db.sqlalchemy_engine import SessionDependency
from api.logging.fastapi_logger import FastAPIStructLogger
from api.model.model_query import base_model_config_select
from api.model_config.model_config_request import validate_inference_parameters_against_model_constraints
from api.thread.chat.chat_request import ChatRequest, CreateToolDefinition
from api.thread.chat.chat_types import ChatStreamOutput
from api.thread.chat.format_pydantic_output import map_pydantic_chunk
from api.thread.chat.mapping import map_messages_to_pydantic_ai_format
from api.thread.chat.pydantic_inference.pydantic_model_service import get_pydantic_model
from api.thread.models.flat_message import FlatMessage
from api.tools.mcp_service import get_general_mcp_servers
from api.tools.tools_service import ToolsServiceDependency
from core.auth.token import Token
from core.message.message_chunk import (
    ErrorChunk,
    ErrorCode,
    StreamEndChunk,
    StreamStartChunk,
)
from core.message.role import Role
from core.object_id import ID
from db.models.inference_opts import InferenceOpts
from db.models.message import Message, create_message_id
from db.models.model_config import ModelConfig, PromptType

logger = FastAPIStructLogger()


class ModelNotFoundError(UnprocessableProblem):
    title = "Model not found"


class ModelNotAvailableError(UnprocessableProblem):
    title = "Model not available"


def merge_inference_options(
    model: ModelConfig, parent_inference_options: InferenceOpts | None, request_inference_options: InferenceOpts
) -> InferenceOpts:
    """
    Combines inference options from the model config, parent message, and request.

    The options are applied in this order this priority, with lower options overwriting higher:
    ```
    model config
    parent message
    request
    ```
    """
    # get the last inference options, either from the parent message or the model defaults if no parent
    default_inference_options = InferenceOpts.from_model_config_defaults(model)

    merged_inference_options = (
        default_inference_options.model_dump()
        # Excluding None from these lets us keep the options from the higher set of options
        | (parent_inference_options.model_dump(exclude_none=True) if parent_inference_options is not None else {})
        | request_inference_options.model_dump(exclude_none=True)
    )

    return InferenceOpts.model_validate(merged_inference_options)


class InvalidParentError(UnprocessableProblem): ...


def build_message_list_from_parent(messages: Sequence[Message], parent_message_id: ID) -> list[Message]:
    messages_dict = {message.id: message for message in messages}
    intermediate_parent_message = messages_dict.get(parent_message_id)

    if intermediate_parent_message is None:
        invalid_parent_message = (
            f"Message with ID {parent_message_id} was not found when trying to access it as a parent"
        )
        raise InvalidParentError(invalid_parent_message)

    message_list: list[Message] = [intermediate_parent_message]

    while message_list[0].parent is not None:
        intermediate_parent_message = messages_dict.get(message_list[0].parent)

        if intermediate_parent_message is None:
            invalid_parent_message = f"Intermediate message in thread with ID {message_list[0].parent} was not found when trying to access it as a parent"
            raise InvalidParentError(invalid_parent_message)

        message_list.insert(0, intermediate_parent_message)

    return message_list


def map_tool_def_to_pydantic(tool: CreateToolDefinition) -> ToolDefinition:
    tool_definition = ToolDefinition(name=tool.name, description=tool.description, metadata={"source": "user"})

    if tool.parameters is not None:
        # Pydantic-AI applies its own empty default if we don't provide anything. This lets us use that default without recreating it
        tool_definition.parameters_json_schema = tool.parameters.model_dump()

    return tool_definition


class ChatService:
    def __init__(
        self,
        message_repository: AsyncMessageRepositoryDependency,
        session: SessionDependency,
        tools_service: ToolsServiceDependency,
    ):
        self.message_repository = message_repository
        self.session = session
        self.tools_service = tools_service

    async def _get_model(self, model_id: str):
        async with self.session.begin():
            stmt = base_model_config_select.where(ModelConfig.id == model_id)
            result = await self.session.scalars(stmt)

            model = result.one_or_none()

            if model is None:
                model_not_found_message = f"Model with ID '{model_id}' not found"
                raise ModelNotFoundError(model_not_found_message)

            if model.prompt_type == PromptType.FILES_ONLY:
                logger.error("Tried to use a files only model in a normal thread stream %s/%s", id, model)

                # HACK: I want OLMoASR to be set up like a normal model but don't want people to stream to it yet
                model_not_available_message = "This model isn't available yet"
                raise ModelNotAvailableError(model_not_available_message)

            return model

    async def _get_parent_and_root_messages(self, parent_message_id: ID | None):
        if parent_message_id is None:
            return None, None

        parent_message = await self.message_repository.get_message_by_id(parent_message_id)
        root_message = (
            await self.message_repository.get_message_by_id(parent_message.root) if parent_message is not None else None
        )

        return parent_message, root_message

    async def _initialize_thread(
        self,
        root_message_id: ID | None,
        parent_message_id: ID | None,
        request: ChatRequest,
        creator_id: str,
        system_prompt: str | None,
        inference_options: InferenceOpts,
        model: ModelConfig,
    ) -> tuple[list[Message], list[Message]]:
        messages = []
        new_messages = []
        new_root_message_id: ID | None = root_message_id

        if root_message_id is not None and parent_message_id is not None:
            thread_messages = await self.message_repository.get_messages_by_root(root_message_id, creator_id)
            existing_thread_messages = build_message_list_from_parent(thread_messages, parent_message_id)

            messages = [*messages, existing_thread_messages]
            if len(messages) > 0:
                new_root_message_id = messages[0].id

        if parent_message_id is None and system_prompt is not None:
            # if parent_message_id is not set we're working with a new thread so we make a new system prompt and make it the root message
            system_message_id = create_message_id()

            if new_root_message_id is None:
                new_root_message_id = system_message_id

            system_message = Message(
                id=system_message_id,
                root=new_root_message_id,
                content=system_prompt,
                creator=creator_id,
                role=Role.System,
                opts=inference_options,
                model_id=model.id,
                model_host=model.host,
            )
            messages.append(system_message)
            new_messages.append(system_message)

        if request.role is Role.User:
            user_message_id = create_message_id()

            if new_root_message_id is None:
                new_root_message_id = user_message_id

            user_message = Message(
                id=user_message_id,
                content=request.content or "",
                input_parts=request.input_parts,
                creator=creator_id,
                role=request.role,
                opts=inference_options,
                root=new_root_message_id,
                model_id=model.id,
                model_host=model.host,
                parent=parent_message_id,
            )

            messages.append(user_message)
            new_messages.append(user_message)

        if request.role is Role.ToolResponse:
            if not request.content:
                missing_content_message = "Tool response messages must have content"
                raise UnprocessableProblem(missing_content_message)

            if not new_root_message_id:
                tool_response_with_no_parent_message = "Tool response messages must have a parent"
                raise UnprocessableProblem(tool_response_with_no_parent_message)

            tool_response_message = Message(
                content=request.content,
                creator=creator_id,
                role=request.role,
                opts=inference_options,
                root=new_root_message_id,
                model_id=model.id,
                model_host=model.host,
            )

            messages.append(tool_response_message)
            new_messages.append(tool_response_message)

        return messages, new_messages

    async def _validate_and_get_thread(
        self,
        request: ChatRequest,
        user: Token,
        model: ModelConfig,
    ) -> tuple[list[Message], list[Message], ID, ID]:
        parent_message, root_message = await self._get_parent_and_root_messages(request.parent)

        merged_inference_options = merge_inference_options(
            model, InferenceOpts.from_message(parent_message), request.inference_options
        )

        validate_inference_parameters_against_model_constraints(model, merged_inference_options)

        root_message_id = root_message.id if root_message is not None else None
        parent_message_id = parent_message.id if parent_message is not None else None

        all_messages, new_messages = await self._initialize_thread(
            root_message_id,
            parent_message_id=parent_message_id,
            request=request,
            creator_id=user.client,
            system_prompt=model.default_system_prompt,
            inference_options=merged_inference_options,
            model=model,
        )

        return (all_messages, new_messages, all_messages[0].id, all_messages[-1].id)

    @staticmethod
    def _get_toolsets(
        model: ModelConfig,
        user_tools: Sequence[CreateToolDefinition] | None,
        mcp_tools: Sequence[str] | None,
    ) -> list[AbstractToolset]:
        if not model.can_call_tools:
            return []

        user_tool_toolset = ExternalToolset([map_tool_def_to_pydantic(tool) for tool in user_tools or []])

        mcp_toolset = CombinedToolset(get_general_mcp_servers())
        filtered_mcp_toolset = mcp_toolset.filtered(lambda _ctx, tool_def: tool_def.name in (mcp_tools or []))

        return [user_tool_toolset, filtered_mcp_toolset]

    @classmethod
    async def _get_chat_stream(
        cls,
        messages: Sequence[ModelMessage],
        user_tools: Sequence[CreateToolDefinition] | None,
        mcp_tools: Sequence[str] | None,
        model: ModelConfig,
    ):
        pydantic_model = get_pydantic_model(model)

        toolsets = cls._get_toolsets(model, user_tools, mcp_tools)

        agent = Agent(
            model=pydantic_model,
            toolsets=toolsets,
            output_type=[str, DeferredToolRequests],
            end_strategy="exhaustive",
        )

        async for event in agent.run_stream_events(
            message_history=messages,
            usage_limits=UsageLimits(request_limit=10),
        ):
            yield event

    async def _handle_stream(
        self,
        messages: Sequence[ModelMessage],
        user_tools: Sequence[CreateToolDefinition] | None,
        mcp_tools: Sequence[str] | None,
        model: ModelConfig,
        user: Token,
        root_message_id: ID,
        parent_message_id: ID,
        new_messages: Sequence[Message],
    ) -> AsyncGenerator[ChatStreamOutput]:
        yield StreamStartChunk(message=root_message_id)

        for new_message in new_messages:
            yield FlatMessage.from_message(new_message)

        event_stream = self._get_chat_stream(
            messages=messages,
            user_tools=user_tools,
            mcp_tools=mcp_tools,
            model=model,
        )

        user_defined_tool_names = [user_tool.name for user_tool in user_tools or []]
        mcp_tool_names = mcp_tools or []

        last_message_id = parent_message_id
        current_message_id = create_message_id()
        new_messages = []

        try:
            async for event in event_stream:
                match event:
                    case AgentRunResultEvent():
                        run_result = event  # noqa: F841
                    case FunctionToolResultEvent():
                        tool_message = Message(
                            content=str(event.result.content),
                            creator=user.client,
                            role=Role.ToolResponse,
                            # TODO: inherit inference options
                            opts=InferenceOpts(),
                            # TODO: get the proper root message with DB saving
                            root=root_message_id,
                            model_id=model.id,
                            model_host=model.host,
                            parent=last_message_id,
                        )

                        new_messages.append(tool_message)
                        last_message_id = tool_message.id
                        yield FlatMessage.from_message(tool_message)

                    case _:
                        # TODO: Figure out how to make new message IDs for new responses properly
                        # if isinstance(event, PartStartEvent) and (isinstance(event.part, (TextPart, ThinkingPart))):
                        # last_message_id = create_message_id()

                        if isinstance(event, FinalResultEvent):
                            current_message_id = create_message_id()

                        yield map_pydantic_chunk(
                            chunk=event,
                            message_id=current_message_id,
                            user_defined_tool_names=user_defined_tool_names,
                            mcp_tool_names=mcp_tool_names,
                        )

        except Exception as e:
            logger.exception("Inference error")
            current_span = trace.get_current_span()
            current_span.set_status(StatusCode.ERROR, description="Inference error")
            yield ErrorChunk(message=last_message_id, error_code=ErrorCode.OTHER_ERROR, error_description=str(e))
            # TODO: Save error chunk on message
            return

        # TODO: yield final thread

        yield StreamEndChunk(message=root_message_id)

        # TODO: below
        # Safety check
        # Upload files
        # Save initial messages/thread to DB
        # Stream message
        # Support custom tool calls
        # Support multimedia
        # If it's a tool response, go down a different path
        # Error handling

    async def stream_chat_message(self, request: ChatRequest, user: Token) -> AsyncGenerator[ChatStreamOutput]:
        model = await self._get_model(request.model)
        all_messages, new_messages, root_message_id, parent_message_id = await self._validate_and_get_thread(
            request, user, model
        )

        agent_messages = map_messages_to_pydantic_ai_format(all_messages)

        return self._handle_stream(
            agent_messages,
            user_tools=request.tool_definitions,
            model=model,
            mcp_tools=request.selected_tools,
            user=user,
            root_message_id=root_message_id,
            parent_message_id=parent_message_id,
            new_messages=new_messages,
        )


ChatServiceDependency = Annotated[ChatService, Depends()]
