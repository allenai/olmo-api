from flask import Blueprint

from src import db
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.v4MessageBlueprint import create_v4_message_blueprint


def create_v4_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage):
    v4_blueprint = Blueprint(name="v4", import_name=__name__)

    v4_blueprint.register_blueprint(
        blueprint=create_v4_message_blueprint(dbc, storage_client=storage_client),
        url_prefix="/message",
        name="message",
    )

    return v4_blueprint
