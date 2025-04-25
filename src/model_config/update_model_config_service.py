from typing import Literal, Union

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


# This is intentionally a union, flask-pydantic-api doesn't generate models if we use the | syntax
UpdateModelConfigRequest = Union[
    UpdateTextOnlyModelConfigRequest, UpdateMultiModalModelConfigRequest
]


def update_model_config(
    model_id: str,
    request: UpdateModelConfigRequest,
    session_maker: sessionmaker[Session],
):
    with session_maker.begin() as session:
        # try:
        # model_to_update = session.get(ModelConfig, model_id)
        # model_to_update
        updated_model = session.execute(
            update(ModelConfig).returning(ModelConfig),
            {"id": model_id, **request.model_dump()},
        )

        return ResponseModel.model_validate(updated_model)
