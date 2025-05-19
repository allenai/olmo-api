from flask import Blueprint
from sqlalchemy.orm import Session, sessionmaker

from src.model_config.model_config_admin_blueprint import create_model_config_admin_blueprint


def create_admin_blueprint(session_maker: sessionmaker[Session]) -> Blueprint:
    admin_blueprint = Blueprint(name="admin", import_name=__name__)

    admin_blueprint.register_blueprint(create_model_config_admin_blueprint(session_maker))

    return admin_blueprint
