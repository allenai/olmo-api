from typing import Any

from db.models.model_config import (
    FilesOnlyModelConfig,
    ModelConfig,
    MultiModalModelConfig,
    PromptType,
)


def get_model_config_class(value: Any) -> type[ModelConfig | MultiModalModelConfig]:
    if not hasattr(value, "prompt_type"):
        msg = "Value must have a prompt_type attribute"
        raise ValueError(msg)

    if value.prompt_type == PromptType.TEXT_ONLY:
        return ModelConfig

    if value.prompt_type == PromptType.FILES_ONLY:
        return FilesOnlyModelConfig

    return MultiModalModelConfig
