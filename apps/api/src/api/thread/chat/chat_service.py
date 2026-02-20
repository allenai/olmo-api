import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from opentelemetry import trace
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import GEN_AI_REQUEST_MODEL
from pydantic_ai import Agent, AgentRunResultEvent, ModelRequest, SystemPromptPart, UserPromptPart

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.logging.fastapi_logger import FastAPIStructLogger
from api.model.model_repository import ModelRepositoryDependency
from api.model_config.model_config_request import validate_inference_parameters_against_model_constraints
from api.thread.chat.chat_request import ChatRequest
from api.thread.chat.input_parts import map_input_parts
from api.thread.chat.mapping import map_messages_to_pydantic_ai_format
from api.thread.chat.pydantic_inference.pydantic_model_service import get_pydantic_model
from api.tools.tools_service import ToolsServiceDependency
from core.auth.token import Token
from core.object_id import ID, NewID
from db.models.inference_opts import InferenceOpts
from db.models.model_config import ModelConfig, PromptType

if TYPE_CHECKING:
    from db.models.message import Message

logger = FastAPIStructLogger()


class ModelNotFoundError(Exception): ...


class ModelNotAvailableError(Exception): ...


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


class InvalidParentError(Exception): ...


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


class ChatService:
    def __init__(
        self,
        message_repository: AsyncMessageRepositoryDependency,
        model_repository: ModelRepositoryDependency,
        tools_service: ToolsServiceDependency,
    ):
        self.message_repository = message_repository
        self.model_repository = model_repository
        self.tools_service = tools_service

    async def _get_model(self, model_id: str):
        model = await self.model_repository.get_one(model_id)

        if model is None:
            raise ModelNotFoundError

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
        inference_options: InferenceOpts,
        model: ModelConfig,
    ):
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

    async def stream_chat_message(
        self,
        request: ChatRequest,
        user: Token,
    ):
        logger.bind(model=request.model, user=user.client)
        trace.get_current_span().set_attributes({GEN_AI_REQUEST_MODEL: request.model, "user": user.client})

        # Only allow new messages, editing can come with PUT

        model = await self._get_model(request.model)

        parent_message, root_message = await self._get_parent_and_root_messages(request.parent)

        merged_inference_options = merge_inference_options(
            model, InferenceOpts.from_message(parent_message), request.inference_options
        )

        validate_inference_parameters_against_model_constraints(model, merged_inference_options)

        agent_messages = await self._map_to_agent_input(
            root_message_id=root_message.id if root_message is not None else None,
            request=request,
            creator_id=user.client,
            system_prompt=root_message.content if root_message is not None else model.default_system_prompt,
            inference_options=merged_inference_options,
            model=model,
        )

        pydantic_model = get_pydantic_model(model)

        agent = Agent(model=pydantic_model)

        async for event in agent.run_stream_events(message_history=agent_messages):
            if isinstance(event, AgentRunResultEvent):
                run_result = event

            yield json.dumps(event)

        # TODO:
        # Safety check
        # Upload files
        # Save initial messages/thread to DB
        # Stream message
        # Support custom tool calls
        # Support multimedia
        # If it's a tool response, go down a different path


ChatServiceDependency = Annotated[ChatService, Depends()]
