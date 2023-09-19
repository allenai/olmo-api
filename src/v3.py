from .v2 import Server as V2Server
from flask import jsonify, request
from .dao import message
from werkzeug import exceptions

class Server(V2Server):
    def messages(self):
        token = self.authn()

        try:
            offset = int(request.args.get("offset", 0))
        except ValueError as e:
            raise exceptions.BadRequest(f"invalid offset: {e}")

        try:
            limit = int(request.args.get("limit", 10))
        except ValueError as e:
            raise exceptions.BadRequest(f"invalid limit: {e}")

        return jsonify(self.dbc.message.list(
            labels_for=token.client,
            creator=request.args.get("creator"),
            deleted="deleted" in request.args,
            opts=message.MessageListOpts(offset, limit),
        ))
