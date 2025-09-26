from typing import Literal, Self

from mistralai import Any
from pydantic import AwareDatetime, ByteSize, Field, HttpUrl, model_validator

from src.api_interface import APIInterface
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from src.dao.engine_models.model_config import (
    FileRequiredToPromptOption,
    ModelConfig,
    ModelHost,
    ModelType,
    PromptType,
)


class BaseModelConfigRequest(APIInterface):
    name: str = Field(min_length=1)
    host: ModelHost
    information_url: HttpUrl | None = Field(default=None)
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

    temperature_default: float | None = None
    temperature_upper: float | None = None
    temperature_lower: float | None = None
    temperature_step: float | None = None

    top_p_default: float | None = None
    top_p_upper: float | None = None
    top_p_lower: float | None = None
    top_p_step: float | None = None

    max_tokens_default: int | None = None
    max_tokens_upper: int | None = None
    max_tokens_lower: int | None = None
    max_tokens_step: int | None = None

    stop_default: list[str] | None = None

    @model_validator(mode="after")
    def check_inference_parameters_against_constraints(self) -> Self:
        validate_inference_params(self, InferenceValidationValues(
            self.max_tokens_default,
            self.temperature_default,
            self.top_p_default,
        ))
        return self


class BaseTextOnlyModelConfigRequest(BaseModelConfigRequest):
    prompt_type: Literal[PromptType.TEXT_ONLY]


class BaseMultiModalModelConfigRequest(BaseModelConfigRequest):
    prompt_type: Literal[PromptType.MULTI_MODAL, PromptType.FILES_ONLY]
    accepted_file_types: list[str]
    max_files_per_message: int | None = Field(default=None)
    require_file_to_prompt: FileRequiredToPromptOption | None = Field(default=None)
    max_total_file_size: ByteSize | None = Field(default=None)
    allow_files_in_followups: bool | None = Field(default=None)


class InferenceValidationValues:
    def __init__(self, max_tokens: int | None = None, temperature: float | None = None, top_p: float | None = None):
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p

def validate_inference_params(model_config: ModelConfig | BaseModelConfigRequest, values: InferenceValidationValues) -> None:
    if values.max_tokens is not None:
        if model_config.max_tokens_lower is not None and values.max_tokens < model_config.max_tokens_lower:
            msg = "Default max tokens must be greater than or equal to the lower limit"
            raise ValueError(msg)
        if model_config.max_tokens_upper is not None and values.max_tokens > model_config.max_tokens_upper:
            msg = "Default max tokens must be less than or equal to the upper limit"
            raise ValueError(msg)

    if values.temperature is not None:
        if model_config.temperature_lower is not None and values.temperature < model_config.temperature_lower:
            msg = "Default temperature must be greater than or equal to the lower limit"
            raise ValueError(msg)
        if model_config.temperature_upper is not None and values.temperature > model_config.temperature_upper:
            msg = "Default temperature must be less than or equal to the upper limit"
            raise ValueError(msg)

    if values.top_p is not None:
        if model_config.top_p_lower is not None and values.top_p < model_config.top_p_lower:
            msg = "Default top_p must be greater than or equal to the lower limit"
            raise ValueError(msg)
        if model_config.top_p_upper is not None and values.top_p > model_config.top_p_upper:
            msg = "Default top_p must be less than or equal to the upper limit"
            raise ValueError(msg)
