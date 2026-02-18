from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import selectin_polymorphic

from api.db.sqlalchemy_engine import SessionDependency
from db.models.model_config import FilesOnlyModelConfig, ModelConfig, MultiModalModelConfig


class ModelRepository:
    def __init__(self, session: SessionDependency):
        self.session = session

    async def get_all(self, *, include_internal_models=False) -> Sequence[ModelConfig]:
        async with self.session.begin():
            polymorphic_loader_opt = selectin_polymorphic(
                ModelConfig, [ModelConfig, MultiModalModelConfig, FilesOnlyModelConfig]
            )

            stmt = select(ModelConfig).options(polymorphic_loader_opt).order_by(ModelConfig.order.asc())

            if not include_internal_models:
                stmt = stmt.filter_by(internal=False)

            result = await self.session.scalars(stmt)

            return result.all()

    async def get_one(self, model_id: str) -> ModelConfig | None:
        async with self.session.begin():
            polymorphic_loader_opt = selectin_polymorphic(
                ModelConfig, [ModelConfig, MultiModalModelConfig, FilesOnlyModelConfig]
            )
            stmt = select(ModelConfig).options(polymorphic_loader_opt).where(ModelConfig.id == model_id)

            result = await self.session.scalars(stmt)
            model_config = result.one_or_none()

            return model_config


ModelRepositoryDependency = Annotated[ModelRepository, Depends()]
