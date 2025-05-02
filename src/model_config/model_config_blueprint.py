from flask import Blueprint, request
from flask_pydantic_api.api_wrapper import pydantic_api
from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from src.auth.auth_utils import user_has_permission
from src.auth.resource_protectors import anonymous_auth_protector, required_auth_protector
from src.config.get_config import get_config
from src.inference.inference_service import get_available_models
from src.model_config.create_model_config_service import (
    ResponseModel,
    RootCreateModelConfigRequest,
    create_model_config,
)
from src.model_config.delete_model_config_service import (
    delete_model_config,
)
from src.model_config.get_model_config_service import (
    RootModelResponse,
    get_model_config,
    get_model_config_admin,
)
from src.model_config.reorder_model_config_service import (
    ReorderModelConfigRequest,
    reorder_model_config,
)
from src.model_config.update_model_config_service import (
    RootUpdateModelConfigRequest,
    update_model_config,
)


def create_model_config_blueprint(session_maker: sessionmaker[Session]) -> Blueprint:
    model_config_blueprint = Blueprint(name="model_config", import_name=__name__)

    @model_config_blueprint.get("/")
    @required_auth_protector(optional=True)
    @pydantic_api(
        name="Get available models and their configuration",
        tags=["v4", "models"],
        openapi_schema_extra={
            "parameters": [
                {
                    "in": "query",
                    "name": "admin",
                    "schema": {"type": "boolean"},
                    "description": "Get the internal models for modification",
                },
            ]
        },
        model_dump_kwargs={"by_alias": True},
    )
    def get_model_configs() -> RootModelResponse:
        is_requesting_admin_models = request.args.get("admin", "false").lower() == "true"
        if is_requesting_admin_models:
            with required_auth_protector.acquire("write:model-config"):
                return get_model_config_admin(session_maker)

        config = get_config()
        if not config.feature_flags.enable_dynamic_model_config:
            return RootModelResponse.model_validate(get_available_models())

        token = anonymous_auth_protector.get_token()
        has_admin_arg = request.args.get("admin")
        should_include_internal_models = has_admin_arg == "true" or user_has_permission(token, "read:internal-models")

        return get_model_config(
            session_maker=session_maker,
            include_internal_models=should_include_internal_models,
        )

    @model_config_blueprint.post("/")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Add a new model",
        tags=["v4", "models", "model configuration"],
        model_dump_kwargs={"by_alias": True},
    )
    def add_model(request: RootCreateModelConfigRequest) -> ResponseModel:
        new_model = create_model_config(request, session_maker)

        return new_model

    @model_config_blueprint.delete("/<model_id>")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Delete a model",
        tags=["v4", "models", "model configuration"],
        model_dump_kwargs={"by_alias": True},
    )
    def delete_model(model_id: str):
        try:
            delete_model_config(model_id, session_maker)
            return "", 204
        except ValueError as e:
            not_found_message = f"No model found with ID {model_id}"
            raise exceptions.NotFound(not_found_message) from e

    @model_config_blueprint.put("/")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Reorder models",
        tags=["v4", "models", "model configuration"],
        model_dump_kwargs={"by_alias": True},
    )
    def reorder_model(request: ReorderModelConfigRequest):
        try:
            reorder_model_config(request, session_maker)
            return "", 204
        except ValueError as e:
            raise exceptions.NotFound from e

    @model_config_blueprint.put("/<model_id>")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Update a model",
        tags=["v4", "models", "model configuration"],
        model_dump_kwargs={"by_alias": True},
    )
    def update_model(
        model_id: str,
        request: RootUpdateModelConfigRequest,
    ) -> ResponseModel:
        updated_model = update_model_config(model_id, request, session_maker)

        if updated_model is None:
            not_found_message = f"No model found with ID {model_id}"
            raise exceptions.NotFound(not_found_message)

        return updated_model

    return model_config_blueprint
