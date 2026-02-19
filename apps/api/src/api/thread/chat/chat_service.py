from typing import Annotated

from fastapi import Depends
from opentelemetry import trace
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import GEN_AI_REQUEST_MODEL  # noqa: PLC2701

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.logging.fastapi_logger import FastAPIStructLogger
from api.model.model_repository import ModelRepositoryDependency
from api.model_config.model_config_request import validate_inference_parameters_against_model_constraints
from api.thread.chat.chat_request import ChatRequest
from core.auth.token import Token
from db.models.inference_opts import InferenceOpts
from db.models.model_config import ModelConfig, PromptType

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


class ChatService:
    def __init__(
        self,
        message_repository: AsyncMessageRepositoryDependency,
        model_repository: ModelRepositoryDependency,
    ):
        self.message_repository = message_repository
        self.model_repository = model_repository

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

    async def _get_parent_and_root_messages(self, parent_message_id: str | None):
        if parent_message_id is None:
            return None, None

        parent_message = await self.message_repository.get_message_by_id(parent_message_id)
        root_message = (
            await self.message_repository.get_message_by_id(parent_message.root) if parent_message is not None else None
        )

        return parent_message, root_message

    async def stream_chat_message(
        self,
        request: ChatRequest,
        user: Token,
    ):
        logger.bind(model=request.model, user=user.client)
        trace.get_current_span().set_attributes({GEN_AI_REQUEST_MODEL: request.model, "user": user.client})

        model = await self._get_model(request.model)

        parent, root = await self._get_parent_and_root_messages(request.parent)

        merged_inference_options = merge_inference_options(
            model, InferenceOpts.from_message(parent), request.inference_options
        )

        validate_inference_parameters_against_model_constraints(model, merged_inference_options)

        # Only allow new messages, editing can come with PUT

        # TODO:
        # Safety check
        # Upload files
        # Save initial messages/thread to DB
        # If it's a tool response, go down a different path
        # Stream message


ChatServiceDependency = Annotated[ChatService, Depends()]
