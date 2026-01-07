from typing import Annotated

from api.db.sqlalchemy import SessionDependency
from api.model_config.response_model import ResponseModel
from db.models.model_config import ModelConfig, MultiModalModelConfig
from fastapi import Depends
from pydantic import RootModel
from sqlalchemy import select
from sqlalchemy.orm import selectin_polymorphic


class AdminModelResponse(RootModel):
    root: list[ResponseModel]


class ModelConfigAdminService:
    def __init__(self, session: SessionDependency):
        self.session = session

    async def get_all(self) -> AdminModelResponse:
        async with self.session.begin():
            polymorphic_loader_opt = selectin_polymorphic(
                ModelConfig, [ModelConfig, MultiModalModelConfig]
            )

            stmt = (
                select(ModelConfig)
                .options(polymorphic_loader_opt)
                .order_by(ModelConfig.order.asc())
            )

            result = await self.session.scalars(stmt)

            processed_results = [
                ResponseModel.model_validate(model) for model in result.all()
            ]

            return AdminModelResponse.model_validate(processed_results)

    async def get_one(
        self, model_id: str
    ) -> ModelConfig | MultiModalModelConfig | None:
        async with self.session.begin():
            polymorphic_loader_opt = selectin_polymorphic(
                ModelConfig, [ModelConfig, MultiModalModelConfig]
            )
            stmt = (
                select(ModelConfig)
                .options(polymorphic_loader_opt)
                .where(ModelConfig.id == model_id)
            )

            result = await self.session.scalars(stmt)
            return result.one_or_none()


ModelConfigAdminServiceDependency = Annotated[ModelConfigAdminService, Depends()]
