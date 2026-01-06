from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    ByteSize,
    Field,
    HttpUrl,
    model_validator,
)

from core.api_interface import APIInterface
from db.models.model_config import (
    FileRequiredToPromptOption,
    ModelConfig,
    ModelHost,
    ModelType,
    PromptType,
)
from infini_gram_api_client.models.available_infini_gram_index_id import (
    AvailableInfiniGramIndexId,
)
from src.dao.message.inference_opts_model import InferenceOpts


def empty_string_to_none(value: str | None) -> str | None:
    if value is None:
        return value

    if value.strip() == "":
        return None

    return value


class BaseModelConfigRequest(APIInterface):
    name: str = Field(min_length=1)
    host: ModelHost
    information_url: HttpUrl | None = Field(default=None)
    description: str = Field(min_length=1)
    model_type: ModelType
    model_id_on_host: str = Field(min_length=1)
    internal: bool = Field(default=True)
    default_system_prompt: Annotated[str | None, AfterValidator(empty_string_to_none)] = Field(default=None)
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
        validate_inference_parameters_against_model_constraints(
            self,
            InferenceOpts(
                max_tokens=self.max_tokens_default,
                temperature=self.temperature_default,
                top_p=self.top_p_default,
            ),
        )
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


def validate_inference_parameters_against_model_constraints(
    model_config: ModelConfig | BaseModelConfigRequest, values: InferenceOpts
) -> None:
    if values.max_tokens is not None:
        if model_config.max_tokens_lower is not None and values.max_tokens < model_config.max_tokens_lower:
            msg = f"Default max tokens must be greater than or equal to the configured lower limit of {model_config.max_tokens_lower}"
            raise ValueError(msg)
        if model_config.max_tokens_upper is not None and values.max_tokens > model_config.max_tokens_upper:
            msg = f"Default max tokens must be less than or equal to the configured upper limit of {model_config.max_tokens_upper}"
            raise ValueError(msg)

    if values.temperature is not None:
        if model_config.temperature_lower is not None and values.temperature < model_config.temperature_lower:
            msg = f"Default temperature must be greater than or equal to the configured lower limit of {model_config.temperature_lower}"
            raise ValueError(msg)
        if model_config.temperature_upper is not None and values.temperature > model_config.temperature_upper:
            msg = f"Default temperature must be less than or equal to the configured upper limit of {model_config.temperature_upper}"
            raise ValueError(msg)

    if values.top_p is not None:
        if model_config.top_p_lower is not None and values.top_p < model_config.top_p_lower:
            msg = f"Default top_p must be greater than or equal to the configured lower limit of {model_config.top_p_lower}"
            raise ValueError(msg)
        if model_config.top_p_upper is not None and values.top_p > model_config.top_p_upper:
            msg = (
                f"Default top_p must be less than or equal to the configured upper limit of {model_config.top_p_upper}"
            )
            raise ValueError(msg)
