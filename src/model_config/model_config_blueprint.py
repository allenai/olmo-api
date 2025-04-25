from authlib.integrations.flask_oauth2 import current_token
from flask import Blueprint, Response, jsonify, request
from flask_pydantic_api.api_wrapper import pydantic_api
from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from src.auth.resource_protectors import required_auth_protector
from src.model_config.create_model_config_service import (
    CreateModelConfigRequest,
    ResponseModel,
    create_model_config,
)
from src.model_config.delete_model_config_service import (
    delete_model_config,
)
from src.model_config.get_model_config_service import get_model_config, get_model_config_admin


def create_model_config_blueprint(session_maker: sessionmaker[Session]) -> Blueprint:
    model_config_blueprint = Blueprint(name="model_config", import_name=__name__)

    @model_config_blueprint.get("/")
    @pydantic_api(name="Get available models and their configuration", tags=["v4", "models"])
    def get_model_configs() -> Response:
        has_admin_arg = request.args.get("admin")
        is_admin = has_admin_arg == "true" or (
            current_token != None
            and "permissions" in current_token
            and "read:internal-models" in current_token["permissions"]
        )

        models = get_model_config_admin(session_maker) if is_admin else get_model_config(session_maker)

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
