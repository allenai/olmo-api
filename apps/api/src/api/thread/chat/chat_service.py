from collections.abc import AsyncGenerator, Sequence
from typing import Annotated

from fastapi import Depends
from fastapi_problem.error import UnprocessableProblem
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from pydantic_ai import (
    Agent,
    AgentRunResultEvent,
    BuiltinToolReturnPart,
    CallDeferred,
    CombinedToolset,
    DeferredToolRequests,
    ExternalToolset,
    FunctionToolResultEvent,
    ModelMessage,
    ModelRequest,
    RunContext,
    SystemPromptPart,
    ToolDefinition,
    UsageLimits,
    UserPromptPart,
)
from pydantic_ai.mcp import MCPServerStreamableHTTP

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.db.sqlalchemy_engine import SessionDependency
from api.logging.fastapi_logger import FastAPIStructLogger
from api.model.model_query import base_model_config_select
from api.model_config.model_config_request import validate_inference_parameters_against_model_constraints
from api.thread.chat.chat_request import ChatRequest, CreateToolDefinition
from api.thread.chat.format_pydantic_output import map_pydantic_chunk
from api.thread.chat.input_parts import map_input_parts
from api.thread.chat.mapping import map_messages_to_pydantic_ai_format
from api.thread.chat.pydantic_inference.pydantic_model_service import get_pydantic_model
from api.thread.models.flat_message import FlatMessage
from api.tools.mcp_service import MCP_SERVERS
from api.tools.tools_service import ToolsServiceDependency
from core.auth.token import Token
from core.message.message_chunk import (
    Chunk,
    ErrorChunk,
    ErrorCode,
    MessageChunk,
    MessageStreamError,
)
from core.message.role import Role
from core.object_id import ID, NewID, new_id_generator
from db.models.inference_opts import InferenceOpts
from db.models.message import Message
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


def user_defined_tool(ctx: RunContext):
    raise CallDeferred({"tool_name": ctx.tool_name})


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


def create_message_id():
    return NewID("msg")


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

    async def get_model(self, model_id: str):
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

    async def _map_to_agent_input(
        self,
        root_message_id: ID | None,
        request: ChatRequest,
        creator_id: str,
        system_prompt: str | None,
        inference_options: InferenceOpts,  # noqa: ARG002
        model: ModelConfig,  # noqa: ARG002
    ) -> list[ModelMessage]:
        user_message = ModelRequest(
            parts=[UserPromptPart(content=map_input_parts(request.input_parts, request.content or ""))]
        )

        if root_message_id is not None and request.parent is not None:
            thread_messages = await self.message_repository.get_messages_by_root(root_message_id, creator_id)
            message_list = build_message_list_from_parent(thread_messages, request.parent)

            return [*map_messages_to_pydantic_ai_format(message_list), user_message]

        if system_prompt is not None:
            user_message.parts = [SystemPromptPart(system_prompt), *user_message.parts]

        return [user_message]

    async def validate_and_map_request(
        self,
        request: ChatRequest,
        user: Token,
        model: ModelConfig,
    ) -> tuple[list[ModelMessage], ID | None]:
        parent_message, root_message = await self._get_parent_and_root_messages(request.parent)

        merged_inference_options = merge_inference_options(
            model, InferenceOpts.from_message(parent_message), request.inference_options
        )

        validate_inference_parameters_against_model_constraints(model, merged_inference_options)

        root_message_id = root_message.id if root_message is not None else None

        agent_messages = await self._map_to_agent_input(
            root_message_id=root_message_id,
            request=request,
            creator_id=user.client,
            system_prompt=root_message.content if root_message is not None else model.default_system_prompt,
            inference_options=merged_inference_options,
            model=model,
        )

        return agent_messages, root_message_id

    async def stream_chat_message(
        self,
        messages: Sequence[ModelMessage],
        user_tools: Sequence[CreateToolDefinition] | None,
        mcp_tools: Sequence[str] | None,
        model: ModelConfig,
        message_id: ID,
        user: Token,
        root_message_id: ID | None,
    ) -> AsyncGenerator[FlatMessage | MessageChunk | MessageStreamError | Chunk | None]:
        # Only allow new messages, editing can come with PUT

        pydantic_model = get_pydantic_model(model)

        user_tool_toolset = ExternalToolset([map_tool_def_to_pydantic(tool) for tool in user_tools or []])

        mcp_toolset = CombinedToolset([
            MCPServerStreamableHTTP(url=server.url, headers=server.headers) for server in MCP_SERVERS
        ])
        filtered_mcp_toolset = mcp_toolset.filtered(lambda _ctx, tool_def: tool_def.name in (mcp_tools or []))

        agent = Agent(
            model=pydantic_model,
            toolsets=[user_tool_toolset, filtered_mcp_toolset],
            output_type=[str, DeferredToolRequests],
            end_strategy="exhaustive",
        )

        last_message_id = message_id
        tool_messages = []

        try:
            async for event in agent.run_stream_events(
                message_history=messages,
                usage_limits=UsageLimits(request_limit=10),
            ):
                match event:
                    case AgentRunResultEvent():
                        run_result = event  # noqa: F841
                    case FunctionToolResultEvent() | BuiltinToolReturnPart():
                        tool_message = Message(
                            content=str(event.result.content),
                            creator=user.client,
                            role=Role.ToolResponse,
                            # TODO: inherit inference options
                            opts=InferenceOpts(),
                            # TODO: get the proper root message with DB saving
                            root=root_message_id or new_id_generator("msg")(),
                            model_id=model.id,
                            model_host=model.host,
                            parent=last_message_id,
                        )

                        tool_messages.append(tool_message)
                        last_message_id = tool_message.id
                        yield FlatMessage.from_message(tool_message)
                    case _:
                        yield map_pydantic_chunk(event, message_id=message_id)

        except Exception as e:
            logger.exception("Inference error")
            current_span = trace.get_current_span()
            current_span.set_status(StatusCode.ERROR, description="Inference error")
            yield ErrorChunk(message=message_id, error_code=ErrorCode.OTHER_ERROR, error_description=str(e))
            return

        # TODO: below
        # Safety check
        # Upload files
        # Save initial messages/thread to DB
        # Stream message
        # Support custom tool calls
        # Support multimedia
        # If it's a tool response, go down a different path
        # Error handling


ChatServiceDependency = Annotated[ChatService, Depends()]
