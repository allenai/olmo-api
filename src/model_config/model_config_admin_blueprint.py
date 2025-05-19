from datetime import UTC, datetime

from flask import Blueprint, current_app
from flask_pydantic_api.api_wrapper import pydantic_api
from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from src.auth.resource_protectors import required_auth_protector
from src.model_config.create_model_config_service import (
    ResponseModel,
    RootCreateModelConfigRequest,
    create_model_config,
)
from src.model_config.delete_model_config_service import (
    delete_model_config,
)
from src.model_config.get_model_config_service import (
    AdminModelResponse,
    get_model_configs_admin,
)
from src.model_config.reorder_model_config_service import (
    ReorderModelConfigRequest,
    reorder_model_config,
)
from src.model_config.update_model_config_service import (
    RootUpdateModelConfigRequest,
    update_model_config,
)


def create_model_config_admin_blueprint(session_maker: sessionmaker[Session]) -> Blueprint:
    model_config_admin_blueprint = Blueprint(name="model_config_admin", import_name=__name__)

    @model_config_admin_blueprint.get("/")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Get full details of a model",
        tags=["v4", "models"],
        model_dump_kwargs={"by_alias": True},
    )
    def get_admin_models() -> AdminModelResponse:
        return get_model_configs_admin(session_maker)

    @model_config_admin_blueprint.post("/")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Add a new model",
        tags=["v4", "models", "model configuration"],
        model_dump_kwargs={"by_alias": True},
    )
    def add_model(request: RootCreateModelConfigRequest) -> ResponseModel:
        new_model = create_model_config(request, session_maker)
        token = required_auth_protector.acquire_token()
        current_app.logger.info({
            "event": "model_config.create",
            "user": token.sub,
            "request": request.model_dump(),
            "date": datetime.now(UTC),
        })

        return new_model

    @model_config_admin_blueprint.delete("/<model_id>")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Delete a model",
        tags=["v4", "models", "model configuration"],
        model_dump_kwargs={"by_alias": True},
    )
    def delete_model(model_id: str):
        token = required_auth_protector.acquire_token()
        try:
            delete_model_config(model_id, session_maker)
            current_app.logger.info({
                "event": "model_config.delete",
                "user": token.sub,
                "model_id": model_id,
                "date": datetime.now(UTC),
            })
            return "", 204
        except ValueError as e:
            not_found_message = f"No model found with ID {model_id}"
            raise exceptions.NotFound(not_found_message) from e

    @model_config_admin_blueprint.put("/")
    @required_auth_protector("write:model-config")
    @pydantic_api(
        name="Reorder models",
        tags=["v4", "models", "model configuration"],
        model_dump_kwargs={"by_alias": True},
    )
    def reorder_model(request: ReorderModelConfigRequest):
        token = required_auth_protector.acquire_token()
        try:
            reorder_model_config(request, session_maker)
            current_app.logger.info({
                "event": "model_config.reorder",
                "user": token.sub,
                "request": request.model_dump(),
                "date": datetime.now(UTC),
            })
            return "", 204
        except ValueError as e:
            raise exceptions.NotFound from e

    @model_config_admin_blueprint.put("/<model_id>")
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
        token = required_auth_protector.acquire_token()
        updated_model = update_model_config(model_id, request, session_maker)

        if updated_model is None:
            not_found_message = f"No model found with ID {model_id}"
            raise exceptions.NotFound(not_found_message)

        current_app.logger.info({
            "event": "model_config.update",
            "user": token.sub,
            "request": {**request.model_dump(), "model_id": model_id},
            "date": datetime.now(UTC),
        })

        return updated_model

    return model_config_admin_blueprint
