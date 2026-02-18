from typing import Annotated

from fastapi import Depends

from api.model.model_repository import ModelRepositoryDependency
from api.model_config.model_config_response import ModelConfigListResponse, ModelConfigResponse


class ModelConfigAdminReadService:
    def __init__(self, model_repository: ModelRepositoryDependency):
        self.model_repository = model_repository

    async def get_all(self) -> ModelConfigListResponse:
        result = await self.model_repository.get_all()

        processed_results = [ModelConfigResponse.model_validate(model) for model in result]

        return ModelConfigListResponse.model_validate(processed_results)

    async def get_one(self, model_id: str) -> ModelConfigResponse | None:
        model_config = await self.model_repository.get_one(model_id)

        if model_config is None:
            return None

        return ModelConfigResponse.model_validate(model_config)


ModelConfigAdminReadServiceDependency = Annotated[ModelConfigAdminReadService, Depends()]
