from typing import Annotated

from pydantic import Field, RootModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectin_polymorphic, sessionmaker

from src.config.Model import Model, MultiModalModel
from src.dao.engine_models.model_config import (
    FilesOnlyModelConfig,
    ModelConfig,
    MultiModalModelConfig,
)
from src.model_config.response_model import ResponseModel
from src.tools.tools_service import get_available_tools


class ModelResponse(RootModel):
    root: list[Annotated[(Model | MultiModalModel), Field(discriminator="prompt_type")]]


def get_model_configs(session_maker: sessionmaker[Session], *, include_internal_models: bool = False) -> ModelResponse:
    with session_maker.begin() as session:
        polymorphic_loader_opt = selectin_polymorphic(
            ModelConfig, [ModelConfig, MultiModalModelConfig, FilesOnlyModelConfig]
        )

        stmt = select(ModelConfig).options(polymorphic_loader_opt).order_by(ModelConfig.order.asc())

        if not include_internal_models:
            stmt = stmt.filter_by(internal=False)

        results = session.scalars(stmt).all()

        return ModelResponse.model_validate(
            results, from_attributes=True, context={"get_available_tools": get_available_tools}
        )


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
