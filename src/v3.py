import dataclasses
import io
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    request,
    send_file,
)
from werkzeug import exceptions
from werkzeug.wrappers import response

from src import config, db, parse, util
from src.auth.auth_service import authn, request_agent
from src.dao import datachip, label, message, paged, token
from src.inference.InferenceEngine import InferenceEngine
from src.log import logging_blueprint
from src.message import MessageBlueprint


@dataclasses.dataclass
class AuthenticatedClient:
    client: str


class Server(Blueprint):
    def __init__(
        self, dbc: db.Client, inference_engine: InferenceEngine, cfg: config.Config
    ):
        super().__init__("v3", __name__)

        self.dbc = dbc
        self.inference_engine = inference_engine
        self.cfg = cfg

        self.get("/whoami")(self.whoami)
        self.get("/login/skiff")(self.login_by_skiff)

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

        self.get("/invite/login")(self.login_by_invite_token)
        self.post("/invite/token")(self.create_invite_token)

        self.post("/datachip")(self.create_datachip)
        self.get("/datachip/<string:id>")(self.datachip)
        self.patch("/datachip/<string:id>")(self.patch_datachip)
        self.get("/datachips")(self.datachips)

        self.register_blueprint(logging_blueprint, url_prefix="/log")
        self.register_blueprint(
            blueprint=MessageBlueprint(dbc, inference_engine, cfg),
            url_prefix="/message",
        )

    def set_auth_cookie(
        self, resp: Response | response.Response, token: token.Token
    ) -> Response | response.Response:
        resp.set_cookie(
            key="token",
            value=token.token,
            expires=token.expires,
            httponly=True,
            secure=True,
            samesite="Strict",
        )
        return resp

    def whoami(self):
        agent = request_agent(self.dbc)
        if agent is None or agent.expired():
            raise exceptions.Unauthorized()

        return self.set_auth_cookie(jsonify(AuthenticatedClient(agent.client)), agent)

    def login_by_skiff(self):
        # Use NGINX mediated auth; see https://skiff.allenai.org/login.html
        email = request.headers.get("X-Auth-Request-Email")
        if email is None:
            # By construction, Skiff Login should guarantee the user header above for all requests, so
            # this shouldn't happen. But if it does, it's clearly a bug in our configuration of "the
            # server", so an HTTP 500 Internal Server Error seems appropriate.
            raise exceptions.InternalServerError()

        # Now we know that the user is logged in by Skiff Login (via its policies), so we can
        # create a new API token.
        agent = self.dbc.token.create(email, token.TokenType.Auth, timedelta(days=7))

        # Figure out where the server should send them after logging in.
        to = urlparse(request.args.get("redirect", self.cfg.server.ui_origin))

        # Prevent redirects to non-authorized origins.
        should_redirect = False
        for o in [self.cfg.server.ui_origin] + self.cfg.server.allowed_redirects:
            trusted = urlparse(o)
            if to.netloc == trusted.netloc and to.scheme == trusted.scheme:
                should_redirect = True
                break
        if not should_redirect:
            raise exceptions.BadRequest("invalid redirect")

        # And send them to the Olmo UI so they continue on with their day using OLMo
        return self.set_auth_cookie(redirect(urlunparse(to)), agent)

    def login_by_invite_token(self):
        # If the user is already logged in, redirect to the UI
        if request_agent(self.dbc) is not None:
            return redirect(self.cfg.server.ui_origin)

        invite = request.args.get("token")
        if invite is None:
            raise exceptions.BadRequest("missing token")

        # Validate the token
        resolved_invite = self.dbc.token.get(invite, token.TokenType.Invite)
        if resolved_invite is None:
            raise exceptions.Unauthorized(
                "Your invite isn't valid. Please contact an administrator if this is an error."
            )

        if resolved_invite.expired():
            raise exceptions.Unauthorized(
                "Your invite has expired. Please contact an adminstrator."
            )

        # Generate a new one
        try:
            nt = self.dbc.token.create(
                resolved_invite.client,
                token.TokenType.Auth,
                timedelta(days=7),
                invite=resolved_invite.token,
            )
        except token.DuplicateInviteError as err:
            raise exceptions.Conflict(str(err))

        # Invalidate the invite token
        expired = self.dbc.token.expire(resolved_invite, token.TokenType.Invite)

        # If invalidation fails, invalidate the newly generated client token and return a 409
        if expired is None:
            self.dbc.token.expire(nt, token.TokenType.Auth)
            raise exceptions.Conflict()

        return self.set_auth_cookie(redirect(self.cfg.server.ui_origin), nt)

    def create_invite_token(self):
        grantor = authn(self.dbc)
        if grantor.client not in self.cfg.server.admins:
            raise exceptions.Forbidden()

        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")

        try:
            expires_in = parse.timedelta_from_str(request.json.get("expires_in", ""))
            if expires_in > timedelta(days=7):
                raise ValueError("expires_in must be <= 7 days")
        except ValueError as e:
            raise exceptions.BadRequest(f"invalid expires_in: {str(e)}")

        grantee = request.json.get("client")
        if grantee is None:
            raise exceptions.BadRequest("missing client")

        invite = self.dbc.token.create(
            grantee, token.TokenType.Invite, expires_in, creator=grantor.client
        )

        path = current_app.url_for("v3.login_by_invite_token", token=invite.token)
        return jsonify({"url": f"{self.cfg.server.api_origin}{path}"})

    def prompts(self):
        authn(self.dbc)
        return jsonify(self.dbc.template.prompts(deleted="deleted" in request.args))

    def prompt(self, id: str):
        authn(self.dbc)
        prompt = self.dbc.template.prompt(id)
        if prompt is None:
            raise exceptions.NotFound()
        return jsonify(prompt)

    def update_prompt(self, id: str):
        agent = authn(self.dbc)
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
        agent = authn(self.dbc)
        prompt = self.dbc.template.prompt(id)
        if prompt is None:
            raise exceptions.NotFound()
        if prompt.author != agent.client:
            raise exceptions.Forbidden()
        return jsonify(self.dbc.template.update_prompt(id, deleted=True))

    def create_prompt(self):
        agent = authn(self.dbc)
        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")

        prompt = self.dbc.template.create_prompt(
            request.json.get("name"), request.json.get("content"), agent.client
        )
        return jsonify(prompt)

    def messages(self):
        agent = authn(self.dbc)
        return jsonify(
            self.dbc.message.list(
                creator=request.args.get("creator"),
                deleted="deleted" in request.args,
                opts=paged.parse_opts_from_querystring(request),
                agent=agent.client,
            )
        )

    def models(self):
        authn(self.dbc)
        # Exclude inferd_compute_source_id from each model in the response and add the model ID (map key).
        return jsonify(
            [
                {
                    "id": m.id,
                    "name": m.name,
                    "description": m.description,
                    "model_type": m.model_type,
                }
                for m in self.cfg.inferd.available_models
            ]
        )

    def schema(self):
        authn(self.dbc)
        return jsonify({"Message": {"InferenceOpts": message.InferenceOpts.schema()}})

    def create_label(self):
        agent = authn(self.dbc)
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

        existing = self.dbc.label.list(
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
        authn(self.dbc)
        label = self.dbc.label.get(id)
        if label is None:
            raise exceptions.NotFound()
        return jsonify(label)

    def labels(self):
        authn(self.dbc)

        try:
            rr = request.args.get("rating")
            rating = label.Rating(int(rr)) if rr is not None else None
        except ValueError as e:
            raise exceptions.BadRequest(str(e))

        ll = self.dbc.label.list(
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
        agent = authn(self.dbc)
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
        agent = authn(self.dbc)
        # Only admins can view completions, since they might be related to private messages.
        if agent.client not in self.cfg.server.admins:
            raise exceptions.Forbidden()
        c = self.dbc.completion.get(id)
        if c is None:
            raise exceptions.NotFound()
        return jsonify(c)

    def create_datachip(self):
        agent = authn(self.dbc)
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
        authn(self.dbc)
        chips = self.dbc.datachip.get([id])
        if len(chips) == 0:
            raise exceptions.NotFound()
        if len(chips) > 1:
            raise exceptions.InternalServerError("multiple chips with same ID")
        return jsonify(chips[0])

    def patch_datachip(self, id: str):
        agent = authn(self.dbc)
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
        authn(self.dbc)
        return jsonify(
            self.dbc.datachip.list_all(
                creator=request.args.get("creator"),
                deleted="deleted" in request.args,
                opts=paged.parse_opts_from_querystring(request),
            )
        )
