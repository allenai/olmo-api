from typing import Literal

from pydantic import AwareDatetime, Field
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from src.api_interface import APIInterface
from src.config.ModelConfig import FileRequiredToPromptOption, ModelHost, ModelType
from src.dao.engine_models.model_config import ModelConfig, PromptType
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
    prompt_type: Literal[PromptType.MULTI_MODAL]
    accepted_file_types: list[str]
    max_files_per_message: int | None = Field(default=None)
    require_file_to_prompt: FileRequiredToPromptOption | None = Field(default=None)
    max_total_file_size: int | None = Field(default=None)
    allow_files_in_followups: bool | None = Field(default=None)


UpdateModelConfigRequest = (
    UpdateTextOnlyModelConfigRequest | UpdateMultiModalModelConfigRequest
)


def update_model_config(
    model_id: str,
    request: UpdateModelConfigRequest,
    session_maker: sessionmaker[Session],
) -> ResponseModel | None:
    with session_maker.begin() as session:
        updated_model = session.scalar(
            update(ModelConfig)
            .where(ModelConfig.id == model_id)
            .values(request.model_dump())
            .returning(ModelConfig),
        )

        return (
            ResponseModel.model_validate(updated_model)
            if updated_model is not None
            else None
        )
