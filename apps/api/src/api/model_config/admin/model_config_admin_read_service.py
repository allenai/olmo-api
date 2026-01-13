from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import selectin_polymorphic

from api.db.sqlalchemy_engine import SessionDependency
from api.model_config.model_config_response_model import ModelConfigListResponseModel, ModelConfigResponseModel
from db.models.model_config import ModelConfig, MultiModalModelConfig


class ModelConfigAdminReadService:
    def __init__(self, session: SessionDependency):
        self.session = session

    async def get_all(self) -> ModelConfigListResponseModel:
        async with self.session.begin():
            polymorphic_loader_opt = selectin_polymorphic(ModelConfig, [ModelConfig, MultiModalModelConfig])

            stmt = select(ModelConfig).options(polymorphic_loader_opt).order_by(ModelConfig.order.asc())

            result = await self.session.scalars(stmt)

            processed_results = [ModelConfigResponseModel.model_validate(model) for model in result.all()]

            return ModelConfigListResponseModel.model_validate(processed_results)

    async def get_one(self, model_id: str) -> ModelConfig | MultiModalModelConfig | None:
        async with self.session.begin():
            polymorphic_loader_opt = selectin_polymorphic(ModelConfig, [ModelConfig, MultiModalModelConfig])
            stmt = select(ModelConfig).options(polymorphic_loader_opt).where(ModelConfig.id == model_id)

            result = await self.session.scalars(stmt)
            return result.one_or_none()


ModelConfigAdminReadServiceDependency = Annotated[ModelConfigAdminReadService, Depends()]
