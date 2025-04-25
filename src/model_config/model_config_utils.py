from typing import Any

from src.dao.engine_models.model_config import (
    ModelConfig,
    MultiModalModelConfig,
    PromptType,
)


def get_model_config_class(value: Any) -> type[ModelConfig | MultiModalModelConfig]:
    if not hasattr(value, "prompt_type"):
        raise ValueError()

    if value.prompt_type == PromptType.TEXT_ONLY:
        return ModelConfig
    else:
        return MultiModalModelConfig
