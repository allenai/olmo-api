import io
import json
from datetime import datetime, timezone

from flask import (
    Blueprint,
    jsonify,
    request,
    send_file,
)
from werkzeug import exceptions

from src import config, db, util
from src.attribution import attribution_blueprint
from src.auth.auth_service import authn
from src.dao import datachip, label, message, paged
from src.inference.inference_service import get_available_models
from src.log import logging_blueprint
from src.message import MessageBlueprint
from src.user import UserBlueprint


class Server(Blueprint):
    def __init__(self, dbc: db.Client):
        super().__init__("v3", __name__)

        self.dbc = dbc

        self.post("/templates/prompt")(self.create_prompt)
        self.get("/templates/prompt/<string:id>")(self.prompt)
        self.patch("/templates/prompt/<string:id>")(self.update_prompt)
        self.delete("/templates/prompt/<string:id>")(self.delete_prompt)
        self.get("/templates/prompts")(self.prompts)

        self.get("/messages")(self.messages)

        self.get("/models")(self.models)

        self.get("/schema")(self.schema)

        self.post("/label")(self.create_label)
        self.get("/label/<string:id>")(self.label)
        self.delete("/label/<string:id>")(self.delete_label)
        self.get("/labels")(self.labels)

        self.get("/completion/<string:id>")(self.completion)

        self.post("/datachip")(self.create_datachip)
        self.get("/datachip/<string:id>")(self.datachip)
        self.patch("/datachip/<string:id>")(self.patch_datachip)
        self.get("/datachips")(self.datachips)

        self.register_blueprint(logging_blueprint, url_prefix="/log")
        self.register_blueprint(
            blueprint=MessageBlueprint(dbc),
            url_prefix="/message",
        )
        self.register_blueprint(blueprint=UserBlueprint(dbc=dbc))
        self.register_blueprint(
            blueprint=attribution_blueprint, url_prefix="/attribution"
        )

    def prompts(self):
        authn()
        return jsonify(self.dbc.template.prompts(deleted="deleted" in request.args))

    def prompt(self, id: str):
        authn()
        prompt = self.dbc.template.prompt(id)
        if prompt is None:
            raise exceptions.NotFound()
        return jsonify(prompt)

    def update_prompt(self, id: str):
        agent = authn()
        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")
        prompt = self.dbc.template.prompt(id)
        if prompt is None:
            raise exceptions.NotFound()
        if prompt.author != agent.client:
            raise exceptions.Forbidden()

        prompt = self.dbc.template.update_prompt(
            id,
            request.json.get("name"),
            request.json.get("content"),
            request.json.get("deleted"),
        )
        if prompt is None:
            raise exceptions.NotFound()
        return jsonify(prompt)

    def delete_prompt(self, id: str):
        agent = authn()
        prompt = self.dbc.template.prompt(id)
        if prompt is None:
            raise exceptions.NotFound()
        if prompt.author != agent.client:
            raise exceptions.Forbidden()
        return jsonify(self.dbc.template.update_prompt(id, deleted=True))

    def create_prompt(self):
        agent = authn()
        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")

        prompt = self.dbc.template.create_prompt(
            request.json.get("name"), request.json.get("content"), agent.client
        )
        return jsonify(prompt)

    def messages(self):
        agent = authn()
        return jsonify(
            self.dbc.message.get_list(
                creator=request.args.get("creator"),
                deleted="deleted" in request.args,
                opts=paged.parse_opts_from_querystring(request),
                agent=agent.client,
            )
        )

    def models(self):
        authn()
        return jsonify(get_available_models())

    def schema(self):
        authn()
        return jsonify({"Message": {"InferenceOpts": message.InferenceOpts.schema()}})

    def create_label(self):
        agent = authn()
        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")

        mid = request.json.get("message")
        msg = self.dbc.message.get(mid)
        if msg is None:
            raise exceptions.BadRequest(f"message {mid} not found")

        try:
            rating = label.Rating(request.json.get("rating"))
        except ValueError as e:
            raise exceptions.BadRequest(str(e))

        existing = self.dbc.label.get_list(
            message=mid,
            creator=agent.client,
        )
        if existing.meta.total != 0:
            raise exceptions.UnprocessableEntity(
                f"message {mid} already has label {existing.labels[0].id}"
            )
        lbl = self.dbc.label.create(
            msg.id, rating, agent.client, request.json.get("comment")
        )
        return jsonify(lbl)

    def label(self, id: str):
        authn()
        label = self.dbc.label.get(id)
        if label is None:
            raise exceptions.NotFound()
        return jsonify(label)

    def labels(self):
        authn()

        try:
            rr = request.args.get("rating")
            rating = label.Rating(int(rr)) if rr is not None else None
        except ValueError as e:
            raise exceptions.BadRequest(str(e))

        ll = self.dbc.label.get_list(
            message=request.args.get("message"),
            creator=request.args.get("creator"),
            deleted="deleted" in request.args,
            rating=rating,
            opts=paged.parse_opts_from_querystring(request, max_limit=1_000_000),
        )

        if "export" not in request.args:
            return jsonify(ll)

        labels = "\n".join([json.dumps(l, cls=util.CustomEncoder) for l in ll.labels])
        filename = f"labels-{int(datetime.now(timezone.utc).timestamp())}.jsonl"
        body = io.BytesIO(labels.encode("utf-8"))

        return send_file(body, as_attachment=True, download_name=filename)

    def delete_label(self, id: str):
        agent = authn()
        label = self.dbc.label.get(id)
        if label is None:
            raise exceptions.NotFound()
        if label.creator != agent.client:
            raise exceptions.Forbidden()
        deleted = self.dbc.label.delete(id)
        if deleted is None:
            raise exceptions.NotFound()
        return jsonify(deleted)

    def completion(self, id: str):
        agent = authn()
        # Only admins can view completions, since they might be related to private messages.
        if agent.client not in config.cfg.server.admins:
            raise exceptions.Forbidden()
        c = self.dbc.completion.get(id)
        if c is None:
            raise exceptions.NotFound()
        return jsonify(c)

    def create_datachip(self):
        agent = authn()
        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")

        name = request.json.get("name", "").strip()
        if name == "":
            raise exceptions.BadRequest("must specify a non-empty name")

        content = request.json.get("content", "").strip()
        if content == "":
            raise exceptions.BadRequest("must specify non-empty content")

        if len(content.encode("utf-8")) > 500 * 1024 * 1024:
            raise exceptions.RequestEntityTooLarge("content must be < 500MB")

        return jsonify(self.dbc.datachip.create(name, content, agent.client))

    def datachip(self, id: str):
        authn()
        chips = self.dbc.datachip.get([id])
        if len(chips) == 0:
            raise exceptions.NotFound()
        if len(chips) > 1:
            raise exceptions.InternalServerError("multiple chips with same ID")
        return jsonify(chips[0])

    def patch_datachip(self, id: str):
        agent = authn()
        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")

        chips = self.dbc.datachip.get([id])
        if len(chips) == 0:
            raise exceptions.NotFound()
        if len(chips) > 1:
            raise exceptions.InternalServerError("multiple chips with same ID")

        chip = chips[0]
        if chip.creator != agent.client:
            raise exceptions.Forbidden()

        deleted = request.json.get("deleted")
        updated = self.dbc.datachip.update(id, datachip.Update(deleted))
        if updated is None:
            raise exceptions.NotFound()
        return jsonify(updated)

    def datachips(self):
        authn()
        return jsonify(
            self.dbc.datachip.list_all(
                creator=request.args.get("creator"),
                deleted="deleted" in request.args,
                opts=paged.parse_opts_from_querystring(request),
            )
        )
