from datetime import UTC, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ByteSize, Field, computed_field

from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from src.dao.engine_models.model_config import FileRequiredToPromptOption, ModelHost, ModelType, PromptType


class ModelBase(BaseModel):
    id: str
    host: ModelHost
    name: str
    description: str
    compute_source_id: str = Field(exclude=True)
    model_type: ModelType
    internal: bool
    system_prompt: str | None = None
    family_id: str | None = None
    family_name: str | None = None
    available_time: AwareDatetime | None = Field(default=None, exclude=True)
    deprecation_time: AwareDatetime | None = Field(default=None, exclude=True)
    accepts_files: bool = Field(default=False)
    can_call_tools: bool = Field(default=False)
    can_think: bool = Field(default=False)
    infini_gram_index: AvailableInfiniGramIndexId | None = Field(default=None)

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

    def __init__(self, **kwargs):
        available_time = kwargs.get("available_time")
        if isinstance(available_time, str):
            kwargs["available_time"] = (
                datetime.fromisoformat(available_time).astimezone(UTC)
                if available_time is not None
                else datetime.min.replace(tzinfo=UTC)
            )

        super().__init__(**kwargs)


class Model(ModelBase):
    prompt_type: Literal[PromptType.TEXT_ONLY] = PromptType.TEXT_ONLY


class MultiModalModel(ModelBase):
    prompt_type: Literal[PromptType.MULTI_MODAL, PromptType.FILES_ONLY]

    accepted_file_types: list[str] = Field(
        description="A list of file type specifiers: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/file#unique_file_type_specifiers",
        examples=[["image/*", "image/png", "image/jpg"], ["video/mp4"]],
    )
    max_files_per_message: int | None = Field(
        default=None,
        description="The maximum number of files the user is allowed to send with a message",
    )
    require_file_to_prompt: FileRequiredToPromptOption = Field(
        default=FileRequiredToPromptOption.NoRequirement,
        description="Defines if a user is required to send files with messages. Not intended to prevent users from sending files with follow-up messages.",
    )
    max_total_file_size: ByteSize | None = Field(
        default=None,
        description="The maximum total file size a user is allowed to send. Adds up the size of every file.",
    )
    allow_files_in_followups: bool = Field(
        default=False,
        description="Defines if a user is allowed to send files with follow-up prompts. To require a file to prompt, use require_file_to_prompt",
    )
