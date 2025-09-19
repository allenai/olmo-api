from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ByteSize,
    Field,
    computed_field,
    field_validator,
)

from src.api_interface import APIInterface
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from src.dao.engine_models.model_config import FileRequiredToPromptOption, ModelHost, ModelType, PromptType
from src.dao.message.inference_opts_model import InferenceOpts


class AvailableTool(APIInterface):
    name: str
    description: str | None = None


def map_datetime_to_utc(datetime: AwareDatetime | None) -> AwareDatetime | None:
    if datetime is None:
        return datetime

    return datetime.astimezone(UTC)


class ModelBase(BaseModel):
    id: str
    host: ModelHost
    name: str
    description: str
    information_url: str | None = None
    model_type: ModelType
    internal: bool
    system_prompt: str | None = None
    family_id: str | None = None
    family_name: str | None = None
    available_time: Annotated[AwareDatetime | None, AfterValidator(map_datetime_to_utc)] = Field(
        default=None, exclude=True
    )
    deprecation_time: Annotated[AwareDatetime | None, AfterValidator(map_datetime_to_utc)] = Field(
        default=None, exclude=True
    )
    accepts_files: bool = Field(default=False)
    can_call_tools: bool = Field(default=False)
    can_think: bool = Field(default=False)
    infini_gram_index: AvailableInfiniGramIndexId | None = Field(default=None)
    default_inference_opts: InferenceOpts | None = Field(default=None)
    available_tools: list[AvailableTool] | None = Field(default=None)

    @field_validator("default_inference_opts", mode="before")
    @classmethod
    def validate_default_inference_opts(cls, value):
        if value is None:
            return InferenceOpts()
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_deprecated(self) -> bool:
        now = datetime.now().astimezone(UTC)

        model_is_not_available_yet = False if self.available_time is None else now < self.available_time
        model_is_after_deprecation_time = False if self.deprecation_time is None else now > self.deprecation_time

        return model_is_not_available_yet or model_is_after_deprecation_time

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_visible(self) -> bool:
        now = datetime.now().astimezone(UTC)

        model_is_available = True if self.available_time is None else now >= self.available_time
        model_is_before_deprecation_time = True if self.deprecation_time is None else now < self.deprecation_time

        return model_is_available and model_is_before_deprecation_time


class Model(ModelBase):
    prompt_type: Literal[PromptType.TEXT_ONLY] = PromptType.TEXT_ONLY


def none_to_false_validator(value: bool | None) -> bool:  # noqa: FBT001
    if value is None:
        return False

    return value


def none_to_no_requirements_validator(value: FileRequiredToPromptOption | None) -> FileRequiredToPromptOption:
    if value is None:
        return FileRequiredToPromptOption.NoRequirement

    return value


class MultiModalModel(ModelBase):
    prompt_type: Literal[PromptType.MULTI_MODAL, PromptType.FILES_ONLY]

    accepts_files: bool = Field(default=True)

    accepted_file_types: list[str] = Field(
        description="A list of file type specifiers: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/file#unique_file_type_specifiers",
        examples=[["image/*", "image/png", "image/jpg"], ["video/mp4"]],
    )
    max_files_per_message: int | None = Field(
        default=None,
        description="The maximum number of files the user is allowed to send with a message",
    )
    require_file_to_prompt: Annotated[
        FileRequiredToPromptOption, BeforeValidator(none_to_no_requirements_validator)
    ] = Field(
        default=FileRequiredToPromptOption.NoRequirement,
        description="Defines if a user is required to send files with messages. Not intended to prevent users from sending files with follow-up messages.",
    )
    max_total_file_size: ByteSize | None = Field(
        default=None,
        description="The maximum total file size a user is allowed to send. Adds up the size of every file.",
    )
    allow_files_in_followups: Annotated[bool, BeforeValidator(none_to_false_validator)] = Field(
        default=False,
        description="Defines if a user is allowed to send files with follow-up prompts. To require a file to prompt, use require_file_to_prompt",
    )
