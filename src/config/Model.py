from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from src.config.ModelConfig import (
    FileRequiredToPromptOption,
    ModelConfig,
    ModelType,
    MultiModalModelConfig,
)


class Model(BaseModel):
    id: str
    name: str
    description: str
    compute_source_id: str = Field(exclude=True)
    model_type: ModelType
    available_time: datetime = Field(exclude=True)
    system_prompt: Optional[str] = None
    family_id: Optional[str] = None
    family_name: Optional[str] = None
    deprecation_time: Optional[datetime] = Field(default=None, exclude=True)

    @computed_field
    @property
    def is_deprecated(self) -> bool:
        now = datetime.now().astimezone(timezone.utc)

        model_is_not_available_yet = now < self.available_time
        model_is_after_deprecation_time = (
            now > self.deprecation_time if self.deprecation_time is not None else False
        )

        return model_is_not_available_yet or model_is_after_deprecation_time

    @computed_field
    @property
    def is_visible(self) -> bool:
        now = datetime.now().astimezone(timezone.utc)

        model_is_available = now >= self.available_time
        model_is_before_deprecation_time = (
            now < self.deprecation_time if self.deprecation_time is not None else True
        )

        return model_is_available and model_is_before_deprecation_time

    def __init__(self, **kwargs):
        available_time = kwargs.get("available_time")
        kwargs["available_time"] = (
            datetime.fromisoformat(available_time).astimezone(timezone.utc)
            if available_time is not None
            else datetime.min.replace(tzinfo=timezone.utc)
        )

        deprecation_time = kwargs.get("deprecation_time")
        kwargs["deprecation_time"] = (
            datetime.min.replace(tzinfo=timezone.utc)
            if kwargs.get("is_deprecated") is True
            else datetime.fromisoformat(deprecation_time).astimezone(timezone.utc)
            if deprecation_time is not None
            else None
        )

        super().__init__(**kwargs)


class MultiModalModel(Model):
    accepts_files: bool = Field(default=False)
    accepted_file_types: list[str]
    max_files_per_message: Optional[int] = Field(default=None)
    require_file_to_prompt: FileRequiredToPromptOption = Field(
        default=FileRequiredToPromptOption.NoRequirement
    )
    max_total_file_size: Optional[int] = Field(default=None)
    allow_files_in_followups: bool = Field(default=False)


def map_model(model_config: ModelConfig | MultiModalModelConfig):
    if model_config.get("accepted_file_types") is not None:
        return MultiModalModel.model_validate(model_config)

    return Model.model_validate(model_config)
