from typing import Annotated

from fastapi import Depends
from pydantic import TypeAdapter

from api.db.sqlalchemy_engine import SessionDependency
from api.model.model_query import base_model_config_select
from api.model.model_response import AvailableTool, ModelListResponse, ModelResponse, ModelValidationContext
from api.tools.tools_service import ToolsServiceDependency
from db.models.model_config import ModelConfig


class ModelReadService:
    def __init__(self, session: SessionDependency, tools_service: ToolsServiceDependency):
        self.session = session
        self.tools_service = tools_service

    async def get_all(self, *, include_internal_models: bool = False) -> ModelListResponse:
        async with self.session.begin():
            stmt = base_model_config_select.order_by(ModelConfig.order.asc())

            if not include_internal_models:
                stmt = stmt.filter_by(internal=False)

            result = await self.session.scalars(stmt)

            model_validation_context = ModelValidationContext(should_show_internal_models=include_internal_models)

            mapped_models = [
                ModelResponse.model_validate(model, from_attributes=True, context=model_validation_context)
                for model in result.all()
            ]

            # Mutating the mapped models list here, would love to have a more elegant way of doing this
            available_tool_list_type_adapter = TypeAdapter(list[AvailableTool])
            for mapped_model in mapped_models:
                mapped_model.root.available_tools = available_tool_list_type_adapter.validate_python(
                    await self.tools_service.get_available_tools(model=mapped_model.root)
                )

            return ModelListResponse.model_validate(mapped_models)


ModelReadServiceDependency = Annotated[ModelReadService, Depends()]
