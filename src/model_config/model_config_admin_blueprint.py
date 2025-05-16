from flask import Blueprint
from flask_pydantic_api.api_wrapper import pydantic_api
from sqlalchemy.orm import Session, sessionmaker

from src.auth.resource_protectors import required_auth_protector
from src.model_config.get_model_config_service import (
    AdminModelResponse,
    get_model_configs_admin,
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

    return model_config_admin_blueprint
