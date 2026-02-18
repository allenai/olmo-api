from typing import Annotated

from fastapi import Depends
from pydantic import TypeAdapter

from api.model.model_repository import ModelRepositoryDependency
from api.model.model_response import AvailableTool, ModelListResponse, ModelResponse, ModelValidationContext
from api.tools.tools_service import ToolsServiceDependency


class ModelReadService:
    def __init__(self, model_repository: ModelRepositoryDependency, tools_service: ToolsServiceDependency):
        self.tools_service = tools_service
        self.model_repository = model_repository

    async def get_all(self, *, include_internal_models: bool = False) -> ModelListResponse:
        result = await self.model_repository.get_all(include_internal_models=include_internal_models)

        model_validation_context = ModelValidationContext(should_show_internal_models=include_internal_models)

        mapped_models = [
            ModelResponse.model_validate(model, from_attributes=True, context=model_validation_context)
            for model in result
        ]

        # Mutating the mapped models list here, would love to have a more elegant way of doing this
        available_tool_list_type_adapter = TypeAdapter(list[AvailableTool])
        for mapped_model in mapped_models:
            mapped_model.root.available_tools = available_tool_list_type_adapter.validate_python(
                await self.tools_service.get_available_tools(model=mapped_model.root)
            )

        return ModelListResponse.model_validate(mapped_models)


ModelReadServiceDependency = Annotated[ModelReadService, Depends()]
