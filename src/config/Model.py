from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, Field, computed_field

from src.config.ModelConfig import (
    FileRequiredToPromptOption,
    ModelConfig,
    ModelHost,
    ModelType,
    MultiModalModelConfig,
)


class Model(BaseModel):
    id: str
    host: ModelHost
    name: str
    description: str
    compute_source_id: str = Field(exclude=True)
    model_type: ModelType
    system_prompt: str | None = None
    family_id: str | None = None
    family_name: str | None = None
    available_time: AwareDatetime | None = Field(default=None, exclude=True)
    deprecation_time: AwareDatetime | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def is_deprecated(self) -> bool:
        now = datetime.now().astimezone(UTC)

        model_is_not_available_yet = False if self.available_time is None else now < self.available_time
        model_is_after_deprecation_time = False if self.deprecation_time is None else now > self.deprecation_time

        return model_is_not_available_yet or model_is_after_deprecation_time

    @computed_field
    @property
    def is_visible(self) -> bool:
        now = datetime.now().astimezone(UTC)

        model_is_available = True if self.available_time is None else now >= self.available_time
        model_is_before_deprecation_time = True if self.deprecation_time is None else now < self.deprecation_time

        return model_is_available and model_is_before_deprecation_time

    def __init__(self, **kwargs):
        available_time = kwargs.get("available_time")
        kwargs["available_time"] = (
            datetime.fromisoformat(available_time).astimezone(UTC)
            if available_time is not None
            else datetime.min.replace(tzinfo=UTC)
        )

        super().__init__(**kwargs)


class MultiModalModel(Model):
    accepts_files: bool = Field(default=False)
    accepted_file_types: list[str]
    max_files_per_message: int | None = Field(default=None)
    require_file_to_prompt: FileRequiredToPromptOption = Field(default=FileRequiredToPromptOption.NoRequirement)
    max_total_file_size: int | None = Field(default=None)
    allow_files_in_followups: bool = Field(default=False)


def map_model_from_config(model_config: ModelConfig | MultiModalModelConfig):
    if model_config.get("accepted_file_types") is not None:
        return MultiModalModel.model_validate(model_config)

    return Model.model_validate(model_config)
