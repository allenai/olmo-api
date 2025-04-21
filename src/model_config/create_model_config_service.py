from datetime import UTC

from pydantic import AwareDatetime, Field
from sqlalchemy.orm import Session, sessionmaker

from src.api_interface import APIInterface
from src.config.ModelConfig import ModelHost, ModelType
from src.dao.engine_models.model_config import ModelConfig, PromptType


class CreateModelConfigRequest(APIInterface):
    id: str
    name: str
    host: ModelHost
    description: str
    model_type: ModelType
    model_id_on_host: str
    internal: bool = Field(default=True)
    prompt_type: PromptType
    default_system_prompt: str | None = Field(default=None)
    family_id: str | None = Field(default=None)
    family_name: str | None = Field(default=None)
    available_time: AwareDatetime | None = Field(default=None)
    deprecation_time: AwareDatetime | None = Field(default=None)


def create_model_config(
    request: CreateModelConfigRequest, session_maker: sessionmaker[Session]
):
    with session_maker.begin() as session:
        new_model = ModelConfig(
            id=request.id,
            name=request.name,
            host=request.host,
            description=request.description,
            model_type=request.model_type,
            model_id_on_host=request.model_id_on_host,
            internal=request.internal,
            prompt_type=request.prompt_type,
            default_system_prompt=request.default_system_prompt,
            family_id=request.family_id,
            family_name=request.family_name,
            available_time=request.available_time.astimezone(UTC)
            if request.available_time is not None
            else None,
            deprecation_time=request.deprecation_time.astimezone(UTC)
            if request.deprecation_time is not None
            else None,
        )
        session.add(new_model)

    return new_model
