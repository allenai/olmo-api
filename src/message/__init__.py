from typing import Generator

from flask import Blueprint, Response, jsonify

from src import db
from src.auth.auth0 import require_auth
from src.message.create_message_service import create_message
from src.message.message_service import delete_message, get_message


class MessageBlueprint(Blueprint):
    def __init__(self, dbc: db.Client):
        super().__init__("message", __name__)

        self.dbc = dbc

        # There used to be a non-streaming endpoint for creating messages. It's gone now.
        # Both URLs are supported for backwards compatibility.
        self.post("/")(self.create_message)
        self.post("/stream")(self.create_message)

        self.get("/<string:id>")(self.message)
        self.delete("/<string:id>")(self.delete_message)

    def create_message(self) -> Response:
        response = create_message(self.dbc)

        if isinstance(response, Generator):
            return Response(response, mimetype="application/jsonl")
        else:
            return jsonify(response)

    def message(self, id: str):
        message = get_message(id=id, dbc=self.dbc)
        return jsonify(message)

    def delete_message(self, id: str):
        deleted_message = delete_message(id=id, dbc=self.dbc)
        return jsonify(deleted_message)
