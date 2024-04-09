from typing import Generator

from flask import Blueprint, Response, jsonify
from inferd.msg.inferd_pb2_grpc import InferDStub

from src import config, db
from src.message.create_message_service import create_message
from src.message.message_service import delete_message, get_message


class MessageBlueprint(Blueprint):
    def __init__(self, dbc: db.Client, inferd: InferDStub, cfg: config.Config):
        super().__init__("message", __name__)

        self.dbc = dbc
        self.inferd = inferd
        self.cfg = cfg

        # There used to be a non-streaming endpoint for creating messages. It's gone now.
        # Both URLs are supported for backwards compatibility.
        self.post("/")(self.create_message)
        self.post("/stream")(self.create_message)

        self.get("/<string:id>")(self.message)
        self.delete("/<string:id>")(self.delete_message)

    def create_message(self) -> Response:
        response = create_message(self.dbc, cfg=self.cfg, inferd=self.inferd)

        if response is Generator:
            return Response(response, mimetype="application/jsonl")
        else:
            return jsonify(response)

    def message(self, id: str):
        message = get_message(id=id, dbc=self.dbc)
        return jsonify(message)

    def delete_message(self, id: str):
        deleted_message = delete_message(id=id, dbc=self.dbc)
        return jsonify(deleted_message)
