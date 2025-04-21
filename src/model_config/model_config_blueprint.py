from flask import Blueprint, Response, jsonify
from flask_pydantic_api.api_wrapper import pydantic_api
from sqlalchemy import select
from sqlalchemy.orm import Session, selectin_polymorphic, sessionmaker

from src.auth.resource_protectors import required_auth_protector
from src.dao.engine_models.model_config import ModelConfig, MultiModalModelConfig
from src.model_config.create_model_config_service import (
    CreateModelConfigRequest,
    create_model_config,
)


def create_model_config_blueprint(session_maker: sessionmaker[Session]) -> Blueprint:
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

    @required_auth_protector("write:model-config")
    @model_config_blueprint.post("/")
    @pydantic_api(name="Add a new model", tags=["v4", "models", "model configuration"])
    def add_model(request: CreateModelConfigRequest) -> Response:
        new_model = create_model_config(request, session_maker)

        return jsonify(new_model)

    return model_config_blueprint
