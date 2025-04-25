from flask import Blueprint, Response, jsonify
from flask_pydantic_api.api_wrapper import pydantic_api
from sqlalchemy import select
from sqlalchemy.orm import Session, selectin_polymorphic, sessionmaker
from werkzeug import exceptions

from src.dao.engine_models.model_config import ModelConfig, MultiModalModelConfig
from src.model_config.create_model_config_service import (
    CreateModelConfigRequest,
    ResponseModel,
    create_model_config,
)
from src.model_config.delete_model_config_service import (
    delete_model_config,
)
from src.model_config.update_model_config_service import (
    UpdateModelConfigRequest,
    update_model_config,
    reorder_model_config
)


def create_model_config_blueprint(session_maker: sessionmaker[Session]) -> Blueprint:
    from src.auth.resource_protectors import required_auth_protector

    model_config_blueprint = Blueprint(name="model_config", import_name=__name__)

    @model_config_blueprint.get("/")
    @pydantic_api(
        name="Get available models and their configuration", tags=["v4", "models"]
    )
    def get_model_configs() -> Response:
        with session_maker.begin() as session:
            polymorphic_loader_opt = selectin_polymorphic(
                ModelConfig, [ModelConfig, MultiModalModelConfig]
            )
            stmt = select(ModelConfig).options(polymorphic_loader_opt)
            rows = session.scalars(stmt).all()

            return jsonify(rows)

    @model_config_blueprint.post("/")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Add a new model",
        tags=["v4", "models", "model configuration"],
        model_dump_kwargs={"by_alias": True},
    )
    def add_model(request: CreateModelConfigRequest) -> ResponseModel:
        new_model = create_model_config(request, session_maker)

        return new_model

    @model_config_blueprint.delete("/<model_id>")
    @required_auth_protector("write:model-config")
    @pydantic_api(name="Delete a model", tags=["v4", "models", "model configuration"])
    def delete_model(model_id: str):
        try:
            delete_model_config(model_id, session_maker)
            return "", 204
        except ValueError:
            raise exceptions.NotFound
        
    
    @model_config_blueprint.put("/")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Reorder models", 
        tags=["v4", "models", "model configuration"])
    def reorder_model(request: ReorderModelConfigRequest):
        try:
            reorder_model_config(request, session_maker)
            return "", 204
        except ValueError as e:
            raise  exceptions.NotFound

    @model_config_blueprint.put("/<model_id>")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Update a model",
        tags=["v4", "models", "model configuration"],
    )
    def update_model(
        model_id: str,
        request: UpdateModelConfigRequest,
    ) -> ResponseModel:
        updated_model = update_model_config(model_id, request, session_maker)

        return updated_model

    return model_config_blueprint
