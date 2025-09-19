from flask import Blueprint
from sqlalchemy.orm import Session, sessionmaker

from src.auth.auth_utils import Permissions, user_has_permission
from src.auth.resource_protectors import anonymous_auth_protector
from src.flask_pydantic_api.api_wrapper import pydantic_api
from src.model_config.get_model_config_service import (
    ModelResponse,
    get_model_configs,
)


def create_model_config_blueprint(session_maker: sessionmaker[Session]) -> Blueprint:
    model_config_blueprint = Blueprint(name="model_config", import_name=__name__)

    @model_config_blueprint.get("/")
    @pydantic_api(
        name="Get available models",
        tags=["v4", "models"],
        model_dump_kwargs={"by_alias": True},
    )
    def get_models() -> ModelResponse:
        token = anonymous_auth_protector.get_token()
        should_include_internal_models = user_has_permission(token, Permissions.READ_INTERNAL_MODELS)

        return get_model_configs(
            session_maker=session_maker,
            include_internal_models=should_include_internal_models,
        )

    return model_config_blueprint
