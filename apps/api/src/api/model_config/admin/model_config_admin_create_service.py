from typing import Annotated

from fastapi import Depends, HTTPException, status
from psycopg.errors import UniqueViolation
from pydantic import Field, RootModel
from sqlalchemy.exc import IntegrityError

from api.db.sqlalchemy_engine import SessionDependency
from api.model_config.model_config_request import (
    BaseMultiModalModelConfigRequest,
    BaseTextOnlyModelConfigRequest,
)
from api.model_config.model_config_response_model import ModelConfigResponseModel
from api.model_config.model_config_utils import get_model_config_class
from core.api_interface import APIInterface


class BaseCreateModelConfigRequest(APIInterface):
    id: str = Field(min_length=1)


class CreateTextOnlyModelConfigRequest(
    BaseCreateModelConfigRequest,
    BaseTextOnlyModelConfigRequest,
): ...


class CreateMultiModalModelConfigRequest(
    BaseCreateModelConfigRequest,
    BaseMultiModalModelConfigRequest,
): ...


class RootCreateModelConfigRequest(RootModel):
    root: CreateTextOnlyModelConfigRequest | CreateMultiModalModelConfigRequest = Field(discriminator="prompt_type")


class ModelConfigAdminCreateService:
    def __init__(self, session: SessionDependency):
        self.session = session

    async def create(self, request: RootCreateModelConfigRequest) -> ModelConfigResponseModel:
        """
        Creates a new ModelConfig

        Args:
            request: The model configuration data (Text | MultiModal)

        Returns:
            ModelConfig response

        Raises:
            HTTPException: 409 if a model config with the given ID already exists
        """
        async with self.session.begin():
            try:
                RequestClass = get_model_config_class(request.root)  # noqa: N806

                new_model = RequestClass(**request.root.model_dump(by_alias=False))

                self.session.add(new_model)
                await self.session.flush()

                return ModelConfigResponseModel.model_validate(new_model)

            except IntegrityError as e:
                # Duplicate ID causes 409 confict error
                if isinstance(e.orig, UniqueViolation):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Model config with id '{request.root.id}' already exists",
                    ) from e
                raise


ModelConfigCreateServiceDependency = Annotated[ModelConfigAdminCreateService, Depends()]
