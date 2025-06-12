from typing import Annotated

from pydantic import ByteSize, Field, RootModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectin_polymorphic, sessionmaker

from src.config.Model import Model, MultiModalModel
from src.config.ModelConfig import FileRequiredToPromptOption
from src.dao.engine_models.model_config import (
    FilesOnlyModelConfig,
    ModelConfig,
    MultiModalModelConfig,
)
from src.model_config.response_model import ResponseModel


class ModelResponse(RootModel):
    root: list[Annotated[(Model | MultiModalModel), Field(discriminator="prompt_type")]]


def map_model(model: ModelConfig) -> MultiModalModel | Model:
    # MultiModalModelConfig instances include FilesOnlyModelConfigs
    if isinstance(model, MultiModalModelConfig):
        return MultiModalModel(
            id=model.id,
            name=model.name,
            host=model.host,
            description=model.description,
            compute_source_id=model.model_id_on_host,
            model_type=model.model_type,
            system_prompt=model.default_system_prompt,
            family_id=model.family_id,
            family_name=model.family_name,
            available_time=model.available_time,
            deprecation_time=model.deprecation_time,
            accepts_files=True,
            accepted_file_types=model.accepted_file_types,
            max_files_per_message=model.max_files_per_message,
            require_file_to_prompt=model.require_file_to_prompt or FileRequiredToPromptOption.NoRequirement,
            max_total_file_size=ByteSize(model.max_total_file_size) if model.max_total_file_size is not None else None,
            allow_files_in_followups=model.allow_files_in_followups or False,
            internal=model.internal,
            prompt_type=model.prompt_type,  # type: ignore
        )

    return Model(
        id=model.id,
        name=model.name,
        host=model.host,
        description=model.description,
        compute_source_id=model.model_id_on_host,
        model_type=model.model_type,
        system_prompt=model.default_system_prompt,
        family_id=model.family_id,
        family_name=model.family_name,
        available_time=model.available_time,
        deprecation_time=model.deprecation_time,
        internal=model.internal,
    )


def get_model_configs(session_maker: sessionmaker[Session], *, include_internal_models: bool = False) -> ModelResponse:
    with session_maker.begin() as session:
        polymorphic_loader_opt = selectin_polymorphic(
            ModelConfig, [ModelConfig, MultiModalModelConfig, FilesOnlyModelConfig]
        )

        stmt = select(ModelConfig).options(polymorphic_loader_opt).order_by(ModelConfig.order.asc())

        if not include_internal_models:
            stmt = stmt.filter_by(internal=False)

        results = session.scalars(stmt).all()

        return ModelResponse.model_validate([map_model(model) for model in results])


class AdminModelResponse(RootModel):
    root: list[ResponseModel]


def get_model_configs_admin(session_maker: sessionmaker[Session]) -> AdminModelResponse:
    with session_maker.begin() as session:
        polymorphic_loader_opt = selectin_polymorphic(ModelConfig, [ModelConfig, MultiModalModelConfig])

        stmt = select(ModelConfig).options(polymorphic_loader_opt).order_by(ModelConfig.order.asc())
        results = session.scalars(stmt).all()

        processed_results = [ResponseModel.model_validate(model) for model in results]

        return AdminModelResponse.model_validate(processed_results)


def get_single_model_config_admin(
    session_maker: sessionmaker[Session], model_id: str
) -> ModelConfig | MultiModalModelConfig | None:
    with session_maker.begin() as session:
        polymorphic_loader_opt = selectin_polymorphic(ModelConfig, [ModelConfig, MultiModalModelConfig])
        stmt = select(ModelConfig).options(polymorphic_loader_opt).where(ModelConfig.id == model_id)

        return session.scalars(stmt).one_or_none()
