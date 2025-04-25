from typing import Literal

from psycopg.errors import UniqueViolation
from pydantic import AwareDatetime, Field, RootModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from src.api_interface import APIInterface
from src.config.ModelConfig import (
    FileRequiredToPromptOption,
    ModelHost,
    ModelType,
)
from src.dao.engine_models.model_config import (
    ModelConfig,
    MultiModalModelConfig,
    PromptType,
)
from src.model_config.response_model import ResponseModel


class BaseCreateModelConfigRequest(APIInterface):
    id: str
    name: str
    host: ModelHost
    description: str
    model_type: ModelType
    model_id_on_host: str
    internal: bool = Field(default=True)
    default_system_prompt: str | None = Field(default=None)
    family_id: str | None = Field(default=None)
    family_name: str | None = Field(default=None)
    available_time: AwareDatetime | None = Field(default=None)
    deprecation_time: AwareDatetime | None = Field(default=None)


class CreateTextOnlyModelConfigRequest(BaseCreateModelConfigRequest):
    prompt_type: Literal[PromptType.TEXT_ONLY]


class CreateMultiModalModelConfigRequest(BaseCreateModelConfigRequest):
    prompt_type: Literal[PromptType.MULTI_MODAL]
    accepted_file_types: list[str]
    max_files_per_message: int | None = Field(default=None)
    require_file_to_prompt: FileRequiredToPromptOption | None = Field(default=None)
    max_total_file_size: int | None = Field(default=None)
    allow_files_in_followups: bool | None = Field(default=None)


# We can't make a discriminated union at the top level so we need to use a RootModel
class RootCreateModelConfigRequest(RootModel):
    root: CreateTextOnlyModelConfigRequest | CreateMultiModalModelConfigRequest = Field(
        discriminator="prompt_type"
    )


def create_model_config(
    request: RootCreateModelConfigRequest, session_maker: sessionmaker[Session]
) -> ResponseModel:
    with session_maker.begin() as session:
        try:
            # polymorphic_loader_opt = selectin_polymorphic(
            #     ModelConfig, [ModelConfig, MultiModalModelConfig]
            # )

            # new_model = session.scalars(
            #     insert(ModelConfig)
            #     .returning(ModelConfig)
            #     .returning(MultiModalModelConfig)
            #     .options(polymorphic_loader_opt),
            #     [request.model_dump()],
            # ).one()

            request_class = (
                ModelConfig
                if request.root.prompt_type is PromptType.TEXT_ONLY
                else MultiModalModelConfig
            )
            new_model = request_class(**request.model_dump())
            # new_model = ModelConfig(
            #     id=request.id,
            #     name=request.name,
            #     host=request.host,
            #     description=request.description,
            #     model_type=request.model_type,
            #     model_id_on_host=request.model_id_on_host,
            #     internal=request.internal,
            #     prompt_type=request.prompt_type,
            #     default_system_prompt=request.default_system_prompt,
            #     family_id=request.family_id,
            #     family_name=request.family_name,
            #     available_time=request.available_time.astimezone(UTC)
            #     if request.available_time is not None
            #     else None,
            #     deprecation_time=request.deprecation_time.astimezone(UTC)
            #     if request.deprecation_time is not None
            #     else None,
            # )
            # session.add(new_model)
            # session.flush()  # This populates the auto-generated things on the new_model
            session.add(new_model)
            session.flush()

            return ResponseModel.model_validate(new_model)

        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                conflict_message = f"{request.root.id} already exists"
                raise exceptions.Conflict(conflict_message) from e

            raise
