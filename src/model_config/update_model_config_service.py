from typing import Literal, cast

from pydantic import AwareDatetime, ByteSize, Field, RootModel
from sqlalchemy.orm import Session, sessionmaker

from src.api_interface import APIInterface
from src.config.ModelConfig import FileRequiredToPromptOption, ModelHost, ModelType
from src.dao.engine_models.model_config import MultiModalModelConfig, PromptType
from src.model_config.model_config_utils import get_model_config_class
from src.model_config.response_model import ResponseModel


class BaseUpdateModelConfigRequest(APIInterface):
    name: str
    host: ModelHost
    description: str
    model_type: ModelType
    model_id_on_host: str
    internal: bool = Field(default=True)
    default_system_prompt: str | None = Field(default=None)
    family_id: str | None = Field(default=None)
    family_name: str | None = Field(default=None)
    available_time: AwareDatetime | None = Field(default=None)
    deprecation_time: AwareDatetime | None = Field(default=None)


class UpdateTextOnlyModelConfigRequest(BaseUpdateModelConfigRequest):
    prompt_type: Literal[PromptType.TEXT_ONLY]


class UpdateMultiModalModelConfigRequest(BaseUpdateModelConfigRequest):
    prompt_type: Literal[PromptType.MULTI_MODAL, PromptType.FILES_ONLY]
    accepted_file_types: list[str]
    max_files_per_message: int | None = Field(default=None)
    require_file_to_prompt: FileRequiredToPromptOption | None = Field(default=None)
    max_total_file_size: ByteSize | None = Field(default=None)
    allow_files_in_followups: bool | None = Field(default=None)


# We can't make a discriminated union at the top level so we need to use a RootModel
class RootUpdateModelConfigRequest(RootModel):
    root: UpdateTextOnlyModelConfigRequest | UpdateMultiModalModelConfigRequest = Field(discriminator="prompt_type")


def update_model_config(
    model_id: str,
    request: RootUpdateModelConfigRequest,
    session_maker: sessionmaker[Session],
) -> ResponseModel | None:
    with session_maker.begin() as session:
        RequestClass = get_model_config_class(request.root)
        model_to_update = session.get(RequestClass, model_id)

        if model_to_update is None:
            return None

        model_to_update.name = request.root.name
        model_to_update.host = request.root.host
        model_to_update.description = request.root.description
        model_to_update.model_type = request.root.model_type
        model_to_update.model_id_on_host = request.root.model_id_on_host
        model_to_update.internal = request.root.internal
        model_to_update.default_system_prompt = request.root.default_system_prompt
        model_to_update.family_id = request.root.family_id
        model_to_update.family_name = request.root.family_name
        model_to_update.available_time = request.root.available_time
        model_to_update.deprecation_time = request.root.deprecation_time
        model_to_update.prompt_type = request.root.prompt_type

        if isinstance(model_to_update, MultiModalModelConfig):
            multi_modal_request = cast(UpdateMultiModalModelConfigRequest, request.root)

            model_to_update.accepted_file_types = multi_modal_request.accepted_file_types
            model_to_update.max_files_per_message = multi_modal_request.max_files_per_message
            model_to_update.require_file_to_prompt = multi_modal_request.require_file_to_prompt
            model_to_update.max_total_file_size = multi_modal_request.max_total_file_size
            model_to_update.allow_files_in_followups = multi_modal_request.allow_files_in_followups

        return ResponseModel.model_validate(model_to_update)
