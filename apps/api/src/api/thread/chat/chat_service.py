import os
from collections.abc import AsyncIterator, Sequence
from typing import Annotated

from fastapi import Depends
from fastapi_problem.error import ForbiddenProblem, UnprocessableProblem
from opentelemetry import trace
from pydantic_ai import (
    AbstractToolset,
    Agent,
    CombinedToolset,
    DeferredToolRequests,
    ExternalToolset,
    ToolDefinition,
)

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.config import settings
from api.db.sqlalchemy_engine import SessionDependency
from api.gcs_dependency import GoogleCloudStorageDependency
from api.logging.fastapi_logger import FastAPIStructLogger
from api.model.model_query import base_model_config_select
from api.model_config.model_config_request import validate_inference_parameters_against_model_constraints
from api.thread.chat.chat_request import ChatRequest, CreateToolDefinition
from api.thread.chat.playground_ui_adapter._adapter import PlaygroundUIAdapter
from api.thread.chat.playground_ui_adapter._util import RunInput
from api.thread.chat.pydantic_inference.pydantic_model_service import get_pydantic_model
from api.thread.chat.pydantic_inference.pydantic_model_settings import pydantic_model_settings
from api.tools.mcp_service import get_general_mcp_servers
from api.tools.tools_service import ToolsServiceDependency
from core.auth.token import Token
from core.message.role import Role
from core.object_id import ID
from core.tools.tool_source import ToolSource
from db.models.inference_opts import InferenceOpts
from db.models.message import Message, create_message_id
from db.models.model_config import ModelConfig, PromptType
from db.models.tool_call import clone_tool_call
from db.models.tool_definitions import ToolDefinition as Ai2ToolDefinition

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
        # exclude_none prevents some issues with calling OpenAI APIs that don't know how to parse null
        tool_definition.parameters_json_schema = tool.parameters.model_dump(exclude_none=True)

    return tool_definition


tracer = trace.get_tracer(__name__)


class ChatService:
    def __init__(
        self,
        message_repository: AsyncMessageRepositoryDependency,
        session: SessionDependency,
        tools_service: ToolsServiceDependency,
        storage: GoogleCloudStorageDependency,
    ):
        self.message_repository = message_repository
        self.session = session
        self.tools_service = tools_service
        self.storage = storage

    @tracer.start_as_current_span(name="ChatService/_get_model")
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

    @tracer.start_as_current_span(name="ChatService/_initialize_thread")
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
        messages: list[Message] = []
        new_messages: list[Message] = []

        if root_message_id is not None and parent_message_id is not None:
            thread_messages = await self.message_repository.get_messages_by_root(root_message_id, creator_id)
            existing_thread_messages = build_message_list_from_parent(thread_messages, parent_message_id)

            messages = [*messages, *existing_thread_messages]

            root_message = messages[-1]
            if root_message.creator != creator_id:
                user_is_not_creator_message = "Cannot create message when not creator"  # words this
                raise ForbiddenProblem(user_is_not_creator_message)

            if root_message.private != request.private:
                visibility_message = "Visibility must be identical for all messages in a thread"
                raise UnprocessableProblem(visibility_message)

        elif system_prompt is not None:
            # if parent_message_id is not set we're working with a new thread so we make a new system prompt and make it the root message
            system_message_id = create_message_id()

            system_message = Message(
                id=system_message_id,
                root=system_message_id,
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
            root_message_id = messages[0].id if messages else user_message_id

            tool_definitions = [
                Ai2ToolDefinition(
                    name=definition.name,
                    description=definition.description,
                    parameters=definition.parameters.model_dump(),
                    tool_source=ToolSource.USER_DEFINED,
                )
                for definition in request.tool_definitions or []
            ]

            parent = messages[-1] if len(messages) > 0 else None

            user_message = Message(
                id=user_message_id,
                content=request.content or "",
                input_parts=request.input_parts,
                creator=creator_id,
                role=request.role,
                opts=inference_options,
                root=root_message_id,
                model_id=model.id,
                model_host=model.host,
                parent=parent.id if parent else None,
                tool_definitions=tool_definitions,
            )
            user_message.parent_ = parent

            messages.append(user_message)
            new_messages.append(user_message)

        if request.role is Role.ToolResponse:
            parent_message = messages[-1]

            if not parent_message.tool_calls:
                parent_has_no_tools_message = "Can not create a tool response. Parent has no tools"
                raise UnprocessableProblem(parent_has_no_tools_message)

            request_tool_call = next(
                (
                    tool_call
                    for tool_call in parent_message.tool_calls
                    if tool_call.tool_call_id == request.tool_call_id
                ),
                None,
            )

            if request_tool_call is None:
                cannot_find_tool_message = "Can not find tool id in last assistant message"
                raise UnprocessableProblem(cannot_find_tool_message)

            tool_response_message = Message(
                content=request.content,
                creator=creator_id,
                role=request.role,
                opts=inference_options,
                root=parent_message.root,
                model_id=model.id,
                model_host=model.host,
                parent=parent_message.id,
                tool_calls=[clone_tool_call(request_tool_call)],
            )
            tool_response_message.parent_ = parent_message

            messages.append(tool_response_message)
            new_messages.append(tool_response_message)

        await self.message_repository.add_many(new_messages)

        return messages, new_messages

    @tracer.start_as_current_span(name="ChatService/_validate_and_get_thread")
    async def _validate_and_get_thread(
        self,
        request: ChatRequest,
        user: Token,
        model: ModelConfig,
    ) -> tuple[list[Message], list[Message], ID, ID, list[Ai2ToolDefinition] | None, InferenceOpts]:
        parent_message = (
            await self.message_repository.get_message_by_id(request.parent) if request.parent is not None else None
        )

        if request.parent is not None and parent_message is None:
            request_parent_doesnt_exists_message = f"Parent message {request.parent} not exist"
            raise UnprocessableProblem(request_parent_doesnt_exists_message)

        if (
            parent_message is not None
            and parent_message.role != Role.ToolResponse
            and parent_message.role == request.role
        ):
            parent_with_same_role_message = "Parent and child must have different roles"
            raise UnprocessableProblem(parent_with_same_role_message)

        merged_inference_options = merge_inference_options(
            model, InferenceOpts.from_message(parent_message), request.inference_options
        )

        validate_inference_parameters_against_model_constraints(model, merged_inference_options)

        root_message_id = parent_message.root if parent_message is not None else None
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

        tool_definitions = next(
            (message.tool_definitions for message in reversed(all_messages) if message.tool_definitions), None
        )

        return (
            all_messages,
            new_messages,
            all_messages[0].id,
            all_messages[-1].id,
            tool_definitions,
            merged_inference_options,
        )

    @staticmethod
    @tracer.start_as_current_span(name="ChatService/_get_toolsets")
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

        # TODO: below
        # Safety check
        # Upload files
        # Save initial messages/thread to DB
        # Support multimedia

    async def stream_chat_message(self, request: ChatRequest, user: Token) -> AsyncIterator[str]:
        model = await self._get_model(request.model)
        (
            all_messages,
            new_messages,
            root_message_id,
            parent_message_id,
            tool_definitions,
            inference_opts,
        ) = await self._validate_and_get_thread(request, user, model)

        tasks = []
        for i, file in enumerate(request.files or []):
            file_extension = os.path.splitext(file.filename)[1] if file.filename is not None else ""
            filename = f"{root_message_id}/{parent_message_id}-{i}{file_extension}"

            upload_response = self.storage.upload_content(filename, file.file, bucket_name=settings)

        # TODO: Determine if parent_message_id is correct or if we should be getting something like request_message_id instead
        # asyncio.gather([self.storage.upload_content(filename=f"{root_message_id}/{parent_message_id}") for i, file in enumerate(request.files)])

        pydantic_model = get_pydantic_model(model)

        model_settings = pydantic_model_settings(
            inference_opts=inference_opts, extra_body=request.extra_parameters, can_think=model.can_think
        )

        toolsets = self._get_toolsets(model, request.tool_definitions, mcp_tools=request.selected_tools)

        agent = Agent(
            model=pydantic_model,
            toolsets=toolsets,
            output_type=[str, DeferredToolRequests],
            end_strategy="exhaustive",
            model_settings=model_settings,
        )

        run_input = RunInput(
            all_messages=all_messages,
            new_messages=new_messages,
            root_message_id=root_message_id,
            parent_message_id=parent_message_id,
            creator=user.client,
            model=model,
            inference_opts=all_messages[-1].opts,
            user_tool_names=[definition.name for definition in request.tool_definitions or []],
            tool_definitions=tool_definitions,
            handle_final_messages=self.message_repository.finalize_thread,
            is_new_thread=not request.parent,
        )

        adapter = PlaygroundUIAdapter(agent, run_input=run_input)

        event_stream = adapter.run_stream()

        return adapter.encode_stream(event_stream)


ChatServiceDependency = Annotated[ChatService, Depends()]
