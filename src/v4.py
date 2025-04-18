from flask import Blueprint
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.config.get_config import get_config
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.v4MessageBlueprint import create_v4_message_blueprint
from src.model_config.model_config_blueprint import create_model_config_blueprint


def create_v4_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage, session_maker: sessionmaker[Session]):
    v4_blueprint = Blueprint(name="v4", import_name=__name__)
    config = get_config()

    v4_blueprint.register_blueprint(
        blueprint=create_v4_message_blueprint(dbc, storage_client=storage_client),
        url_prefix="/message",
        name="message",
    )

    if config.feature_flags.enable_dynamic_model_config:
        v4_blueprint.register_blueprint(
            create_model_config_blueprint(session_maker), url_prefix="/models", name="models"
        )

    return v4_blueprint
