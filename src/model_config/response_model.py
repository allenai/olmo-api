from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, ByteSize, Field, RootModel, computed_field

from src.api_interface import APIInterface
from src.config.ModelConfig import FileRequiredToPromptOption, ModelHost, ModelType
from src.dao.engine_models.model_config import PromptType


class ModelAvailability(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRERELEASE = "prerelease"


class BaseResponseModel(APIInterface):
    id: str
    host: ModelHost
    name: str
    description: str
    model_type: ModelType
    model_id_on_host: str
    internal: bool
    order: int
    default_system_prompt: str | None = Field(default=None)
    can_call_tools: bool

    @computed_field  # type:ignore
    @property
    def availability(self) -> ModelAvailability:
        if self.internal:
            return ModelAvailability.INTERNAL

        if self.available_time is not None and self.available_time > datetime.now(tz=UTC):
            return ModelAvailability.PRERELEASE

        return ModelAvailability.PUBLIC

    family_id: str | None = Field(default=None)
    family_name: str | None = Field(default=None)

    available_time: AwareDatetime | None = Field(default=None)
    deprecation_time: AwareDatetime | None = Field(default=None)

    created_time: AwareDatetime
    updated_time: AwareDatetime


class TextOnlyResponseModel(BaseResponseModel):
    prompt_type: Literal[PromptType.TEXT_ONLY]


class MultiModalResponseModel(BaseResponseModel):
    prompt_type: Literal[PromptType.MULTI_MODAL, PromptType.FILES_ONLY]
    accepted_file_types: list[str]
    max_files_per_message: int | None = Field(default=None)
    require_file_to_prompt: FileRequiredToPromptOption | None = Field(default=None)
    max_total_file_size: ByteSize | None = Field(default=None)
    allow_files_in_followups: bool | None = Field(default=None)


class ResponseModel(RootModel):
    root: Annotated[
        TextOnlyResponseModel | MultiModalResponseModel,
        Field(discriminator="prompt_type"),
    ]
