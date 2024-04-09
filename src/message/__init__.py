from flask import Blueprint, jsonify, request, Response, redirect, current_app, send_file
from werkzeug import exceptions
from werkzeug.wrappers import response
from datetime import timedelta
from inferd.msg.inferd_pb2_grpc import InferDStub
from inferd.msg.inferd_pb2 import InferRequest
from google.protobuf.struct_pb2 import Struct
from google.protobuf import json_format

from src.auth.auth_service import authn, request_agent
from src.message import MessageBlueprint
from src import db, util, auth, config, parse
from src.dao import message, label, completion, token, datachip, paged
from typing import Generator, Optional
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timezone
from enum import StrEnum
from src.log import logging_blueprint

import dataclasses
import os
import json
import io
import grpc

from src.message.message_service import create_message

class MessageBlueprint(Blueprint):
    def __init__(self, dbc: db.Client, inferd: InferDStub, cfg: config.Config):
        super().__init__("v3", __name__)

        self.dbc = dbc
        self.inferd = inferd
        self.cfg = cfg
        
         # There used to be a non-streaming endpoint for creating messages. It's gone now.
        # Both URLs are supported for backwards compatibility.
        self.post("/message")(self.create_message)
        self.post("/message/stream")(self.create_message)

        self.get("/message/<string:id>")(self.message)
        self.delete("/message/<string:id>")(self.delete_message)
        
    def create_message(self) -> Response:
        response = create_message(self.dbc, cfg=self.cfg, inferd=self.inferd)
        
        if (response is Generator):
            return Response(response, mimetype="application/jsonl")
        else: 
            return jsonify(response)

    def message(self, id: str):
        agent = self.authn()
        message = self.dbc.message.get(id, agent=agent.client)
        if message is None:
            raise exceptions.NotFound()
        if message.creator != agent.client and message.private:
            raise exceptions.Forbidden("You do not have access to that private message.")
        return jsonify(message)

    def delete_message(self, id: str):
        agent = self.authn()
        message = self.dbc.message.get(id)
        if message is None:
            raise exceptions.NotFound()
        if message.creator != agent.client:
            raise exceptions.Forbidden()
        deleted = self.dbc.message.delete(id, agent=agent.client)
        if deleted is None:
            raise exceptions.NotFound()
        return jsonify(deleted)
