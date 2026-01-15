from typing import Annotated

from fastapi import Depends
from sqlalchemy import select, update

from api.db.sqlalchemy_engine import SessionDependency
from api.model_config.model_config_response import ModelConfigResponse
from core.api_interface import APIInterface
from db.models.model_config import ModelConfig


class ModelOrder(APIInterface):
    id: str
    order: int


class ReorderModelConfigRequest(APIInterface):
    ordered_models: list[ModelOrder]


class ModelConfigAdminReorderService:
    def __init__(self, session: SessionDependency):
        self.session = session

    async def reorder(self, request: ReorderModelConfigRequest) -> None:
        """
        Reorders ModelConfigs

        Args:
            request: list of {id, order} objects

        Returns:
            None
        """
        async with self.session.begin():
            requested_ids = [model.id for model in request.ordered_models]

            stmt = select(ModelConfig.id).where(ModelConfig.id.in_(requested_ids))
            result = await self.session.scalars(stmt)
            existing_ids = result.all()

            missing_ids = set(requested_ids) - set(existing_ids)

            if missing_ids:
                missing_id_msg = f"Model(s) not found: {', '.join(missing_ids)}"
                raise ValueError(missing_id_msg)

            await self.session.execute(
                update(ModelConfig),
                [{"id": model.id, "order": model.order} for model in request.ordered_models],
            )


ModelConfigAdminReorderServiceDependency = Annotated[ModelConfigAdminReorderService, Depends()]
