from typing import Annotated

from fastapi import Depends
from sqlalchemy.sql import select

from api.db.sqlalchemy_engine import SessionDependency
from api.service_errors import NotFoundError
from db.models.model_config import ModelConfig


class ModelConfigAdminDeleteService:
    def __init__(self, session: SessionDependency):
        self.session = session

    async def delete(self, model_id: str) -> None:
        """
        Deletes a ModelConfig

        Args:
            model_id: the model ID

        Returns:
            None

        Raises:
            ValueError: if a model config with the given ID isn't found
        """
        async with self.session.begin():
            stmt = select(ModelConfig).where(ModelConfig.id == model_id)
            result = await self.session.scalars(stmt)
            delete_model = result.one_or_none()

            if not delete_model:
                model_not_found_msg = f"No model found with ID {model_id}"
                raise NotFoundError(model_not_found_msg)

            await self.session.delete(delete_model)


ModelConfigAdminDeleteServiceDepenecy = Annotated[ModelConfigAdminDeleteService, Depends()]
