from flask import Blueprint, jsonify

from src import db
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.message_service import delete_message as delete_message_service
from src.message.message_service import get_message


def create_v3_message_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage) -> Blueprint:
    v3_message_blueprint = Blueprint(name="message", import_name=__name__)

    @v3_message_blueprint.get("/<string:id>")
    def message(id: str):
        message = get_message(id=id, dbc=dbc)
        print(message)
        return jsonify(message)

    @v3_message_blueprint.delete("/<string:id>")
    def delete_message(id: str):
        deleted_message = delete_message_service(id=id, dbc=dbc, storage_client=storage_client)
        return jsonify(deleted_message)

    return v3_message_blueprint
