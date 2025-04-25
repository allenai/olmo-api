from authlib.integrations.flask_oauth2 import current_token
from flask import Blueprint, Response, jsonify, request
from flask_pydantic_api.api_wrapper import pydantic_api
from sqlalchemy import select
from sqlalchemy.orm import Session, selectin_polymorphic, sessionmaker
from werkzeug import exceptions

from src.auth.resource_protectors import required_auth_protector
from src.dao.engine_models.model_config import ModelConfig, MultiModalModelConfig
from src.model_config.create_model_config_service import (
    CreateModelConfigRequest,
    ResponseModel,
    create_model_config,
)
from src.model_config.delete_model_config_service import (
    delete_model_config,
)


def create_model_config_blueprint(session_maker: sessionmaker[Session]) -> Blueprint:
    model_config_blueprint = Blueprint(name="model_config", import_name=__name__)

    @model_config_blueprint.get("/")
    @pydantic_api(name="Get available models and their configuration", tags=["v4", "models"])
    def get_model_configs() -> Response:
        is_admin = request.args.get("admin")

        with session_maker.begin() as session:
            polymorphic_loader_opt = selectin_polymorphic(ModelConfig, [ModelConfig, MultiModalModelConfig])
            stmt = select(ModelConfig).options(polymorphic_loader_opt)
            rows = session.scalars(stmt).all()

            # return everything for admin roles
            if is_admin == "true" or (
                "permissions" in current_token and "read:internal-models" in current_token.permissions
            ):
                models = list(rows)
                models.sort(key=lambda m: m.order)
                return jsonify(models)

            # otherwise, filter out internal models
            models = list(filter(lambda m: not m.internal, rows))
            models.sort(key=lambda m: m.order)

            return jsonify(models)

    @model_config_blueprint.post("/")  # type: ignore
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

    return model_config_blueprint
