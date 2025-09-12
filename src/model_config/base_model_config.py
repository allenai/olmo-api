from typing import Literal

from pydantic import AwareDatetime, ByteSize, Field

from src.api_interface import APIInterface
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from src.dao.engine_models.model_config import (
    FileRequiredToPromptOption,
    ModelHost,
    ModelType,
    PromptType,
)


class BaseModelConfigRequest(APIInterface):
    name: str = Field(min_length=1)
    host: ModelHost
    information_url: str | None = Field(default=None)
    description: str = Field(min_length=1)
    model_type: ModelType
    model_id_on_host: str = Field(min_length=1)
    internal: bool = Field(default=True)
    default_system_prompt: str | None = Field(default=None)
    family_id: str | None = Field(default=None)
    family_name: str | None = Field(default=None)
    available_time: AwareDatetime | None = Field(default=None)
    deprecation_time: AwareDatetime | None = Field(default=None)
    can_call_tools: bool = Field(default=False)
    can_think: bool = Field(default=False)
    infini_gram_index: AvailableInfiniGramIndexId | None = Field(default=None)


class BaseTextOnlyModelConfigRequest(BaseModelConfigRequest):
    prompt_type: Literal[PromptType.TEXT_ONLY]


class BaseMultiModalModelConfigRequest(BaseModelConfigRequest):
    prompt_type: Literal[PromptType.MULTI_MODAL, PromptType.FILES_ONLY]
    accepted_file_types: list[str]
    max_files_per_message: int | None = Field(default=None)
    require_file_to_prompt: FileRequiredToPromptOption | None = Field(default=None)
    max_total_file_size: ByteSize | None = Field(default=None)
    allow_files_in_followups: bool | None = Field(default=None)
