from pydantic import AwareDatetime, Field

from src.api_interface import APIInterface
from src.config.ModelConfig import ModelType
from src.dao.engine_models.model_config import PromptType


class ResponseModel(APIInterface):
    id: str
    host: str
    description: str
    model_type: ModelType
    model_id_on_host: str
    internal: bool
    prompt_type: PromptType
    order: int
    default_system_prompt: str | None = Field(default=None)

    family_id: str | None = Field(default=None)
    family_name: str | None = Field(default=None)

    available_time: AwareDatetime | None = Field(default=None)
    deprecation_time: AwareDatetime | None = Field(default=None)

    created_time: AwareDatetime
    updated_time: AwareDatetime
