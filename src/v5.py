from flask import Blueprint
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.v5_messages_blueprint import create_v5_messages_blueprint


def create_v5_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage, session_maker: sessionmaker[Session]):
    v5_blueprint = Blueprint(name="v5", import_name=__name__)

    v5_blueprint.register_blueprint(
        blueprint=create_v5_messages_blueprint(dbc, storage_client=storage_client, session_maker=session_maker),
        url_prefix="/messages",
        name="messages",
    )

    return v5_blueprint
