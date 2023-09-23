from flask import Blueprint, jsonify, current_app, request, Response, redirect, current_app
from werkzeug import exceptions
from werkzeug.wrappers import response
from datetime import datetime, timezone, timedelta
from inferd.msg.inferd_pb2_grpc import InferDStub
from inferd.msg.inferd_pb2 import InferRequest
from google.protobuf.struct_pb2 import Struct
from google.protobuf.timestamp_pb2 import Timestamp
from . import db, util, auth, dsearch, config
from .dao.token import Token, TokenType
from .dao import message, label, completion
from typing import Optional

import dataclasses
import os
import json

@dataclasses.dataclass
class AuthenticatedClient:
    client: str

class Server(Blueprint):
    def __init__(self, dbc: db.Client, inferd: InferDStub, didx: dsearch.Client, cfg: config.Config):
        super().__init__("v3", __name__)

        self.dbc = dbc
        self.inferd = inferd
        self.didx = didx
        self.cfg = cfg

        self.get("/whoami")(self.whoami)

        self.post("/templates/prompt")(self.create_prompt)
        self.get("/templates/prompt/<string:id>")(self.prompt)
        self.patch("/templates/prompt/<string:id>")(self.update_prompt)
        self.delete("/templates/prompt/<string:id>")(self.delete_prompt)
        self.get("/templates/prompts")(self.prompts)

        # There used to be a non-streaming endpoint for creating messages. It's gone now.
        # Both URLs are supported for backwards compatibility.
        self.post("/message")(self.create_message)
        self.post("/message/stream")(self.create_message)

        self.get("/message/<string:id>")(self.message)
        self.delete("/message/<string:id>")(self.delete_message)
        self.get("/messages")(self.messages)

        self.get("/schema")(self.schema)

        self.post("/label")(self.create_label)
        self.get("/label/<string:id>")(self.label)
        self.delete("/label/<string:id>")(self.delete_label)
        self.get("/labels")(self.labels)

        self.get("/completions")(self.completions)

        self.get("/data/search")(self.data_search)
        self.get("/data/doc/<string:id>")(self.data_doc)
        self.get("/data/meta")(self.data_meta)

        self.get("/login/<string:token>")(self.login_by_url)
        self.post("/login")(self.create_login_url)

    def token(self) -> Optional[Token]:
        provided = request.cookies.get(
            "token",
            default=auth.token_from_request(request)
        )
        if provided is None:
            return None
        return self.dbc.token.get(provided, TokenType.Client)

    def authn(self) -> Token:
        token = self.token()
        if token is None or token.expired():
            raise exceptions.Unauthorized()

        current_app.logger.info({
            "path": request.path,
            "message": f"authorized client {token.client}",
            "client": token.client,
            "created": token.created,
            "expires": token.expires,
        })

        return token

    def set_auth_cookie(self, resp: Response | response.Response, token: Token) -> Response | response.Response:
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
        token = self.token()
        if token is None or token.expired():
            # Use NGINX mediated auth; see https://skiff.allenai.org/login.html
            email = request.headers.get("X-Auth-Request-Email")
            if email is None:
                raise exceptions.Unauthorized()

            token = self.dbc.token.create(email, TokenType.Client, timedelta(days=7))

        return self.set_auth_cookie(jsonify(AuthenticatedClient(token.client)), token)

    def login_by_url(self, token: str):
        if self.token() is not None:
            raise exceptions.Conflict("already logged in")

        # Validate the token
        resolved = self.dbc.token.get(token, TokenType.Login)
        if resolved is None or resolved.expired():
            raise exceptions.Unauthorized()

        # Generate a new one
        nt = self.dbc.token.create(resolved.client, TokenType.Client, timedelta(days=7))

        # Invalidate the login token
        expired = self.dbc.token.expire(resolved)
        # If invalidation fails, invalidate the newly generated client token and return a 500
        if expired is None:
            self.dbc.token.expire(nt)
            raise exceptions.InternalServerError()

        return self.set_auth_cookie(redirect(self.cfg.server.ui_origin), nt)

    def create_login_url(self):
        token = self.authn()
        if token.client not in self.cfg.server.admins:
            raise exceptions.Forbidden()

        try:
            expires_in = int(request.args.get("expires_in", "24"))
            if expires_in <= 0:
                raise exceptions.BadRequest("expires_in must be positive")
            if expires_in > 7 * 24:
                raise exceptions.BadRequest("expires_in must be <= 7 days")
        except ValueError as e:
            raise exceptions.BadRequest(str(e))

        login_token = self.dbc.token.create(token.client, TokenType.Login, timedelta(hours=expires_in))
        path = current_app.url_for("v3.login_by_url", token=login_token.token)
        return jsonify({ "url": f"{self.cfg.server.api_origin}{path}" })

    def prompts(self):
        self.authn()
        return jsonify(self.dbc.template.prompts(deleted="deleted" in request.args))

    def prompt(self, id: str):
        self.authn()
        prompt = self.dbc.template.prompt(id)
        if prompt is None:
            raise exceptions.NotFound()
        return jsonify(prompt)

    def update_prompt(self, id: str):
        token = self.authn()
        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")
        prompt = self.dbc.template.prompt(id)
        if prompt is None:
            raise exceptions.NotFound()
        if prompt.author != token.client:
            raise exceptions.Forbidden()

        prompt = self.dbc.template.update_prompt(
            id,
            request.json.get("name"),
            request.json.get("content"),
        )
        return jsonify(prompt)

    def delete_prompt(self, id: str):
        token = self.authn()
        prompt = self.dbc.template.prompt(id)
        if prompt is None:
            raise exceptions.NotFound()
        if prompt.author != token.client:
            raise exceptions.Forbidden()
        return jsonify(self.dbc.template.delete_prompt(id))

    def create_prompt(self):
        token = self.authn()
        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")

        prompt = self.dbc.template.create_prompt(
            request.json.get("name"),
            request.json.get("content"),
            token.client
        )
        return jsonify(prompt)

    def create_message(self):
        token = self.authn()
        if request.json is None:
            raise exceptions.BadRequest("no request body")

        pid = request.json.get("parent")
        parent = self.dbc.message.get(pid) if pid is not None else None
        if pid is not None and parent is None:
            raise exceptions.BadRequest(f"parent message {pid} not found")

        try:
            ropts = request.json.get("opts")
            opts = message.InferenceOpts.from_request(ropts) if ropts is not None else message.InferenceOpts()
        except ValueError as e:
            raise exceptions.BadRequest(str(e))

        if opts.n > 1:
            raise exceptions.BadRequest("n > 1 not supported when streaming")

        # TODO: remove when logprobs are supported by the InferD worker
        if opts.logprobs > 0:
            raise exceptions.BadRequest("logprobs not supported when streaming")

        content = request.json.get("content")
        if content.strip() == "":
            raise exceptions.BadRequest("empty content")

        try:
            role = message.Role(request.json.get("role", str(message.Role.User)))
        except ValueError as e:
            raise exceptions.BadRequest(str(e))

        if role == message.Role.Assistant and parent is None:
            raise exceptions.BadRequest("assistant messages must have a parent")

        if parent is not None and parent.role == role:
            raise exceptions.BadRequest("parent and child must have different roles")

        original = request.json.get("original")
        if original is not None and parent is not None and original == parent.id:
            raise exceptions.BadRequest("original message cannot be parent")

        msg = self.dbc.message.create(
            content,
            token.client,
            role,
            opts,
            root=parent.root if parent is not None else None,
            parent=parent.id if parent is not None else None,
            template=request.json.get("template"),
            final=role==message.Role.Assistant,
            original=original
        )

        if msg.role == message.Role.Assistant:
            return jsonify(msg)

        # Resolve the message chain if we need to.
        chain = [msg]
        if parent is not None:
            root = self.dbc.message.get(parent.root)
            assert root is not None
            msgs = message.Message.group_by_id(root.flatten())
            while chain[-1].parent is not None:
                chain.append(msgs[chain[-1].parent])
            chain.reverse()

        input = Struct()
        input.update({
            "messages": [ { "role": m.role, "content": m.content } for m in chain ],
            "opts": dataclasses.asdict(msg.opts),
        })
        deadline = Timestamp()
        deadline.FromDatetime(datetime.now(tz=timezone.utc) + timedelta(seconds=120))

        model = request.json.get("model", "meta-llama/Llama-2-70b-chat-hf")
        req = InferRequest(model_id=model, input=input, deadline=deadline)

        # Create a message that will eventually capture the streamed response.
        # TODO: should handle exceptions mid-stream by deleting and/or finalizing the message
        reply = self.dbc.message.create(
            "",
            token.client,
            message.Role.Assistant,
            msg.opts,
            root=msg.root,
            parent=msg.id,
            final=False
        )

        # Update the parent message to include the reply.
        msg = dataclasses.replace(msg, children=[reply])

        # Capture the SHA, as the current_app context is lost in the generator.
        sha = os.environ["SHA"] if not current_app.debug else "DEV"

        def stream():
            # We keep track of each chunk and the timing information per-chunk
            # so that we can manifest a completion at the end. This will go
            # away when InferD stores this I/O.
            chunks = []
            gen, queue = 0, 0

            # First yield the new user message
            yield json.dumps(msg, cls=util.CustomEncoder) + "\n"

            # Now yield each chunk as it's returned.
            for resp in self.inferd.Infer(req, wait_for_ready=True):
                chunks.append(message.MessageChunk(reply.id, resp.output["text"]))
                gen += resp.inference_time.ToMilliseconds()
                queue = resp.queue_time.ToMilliseconds()
                yield json.dumps(chunks[-1], cls=util.CustomEncoder) + "\n"

            # The generation is complete. Store it.
            # TODO: InferD should store this so that we don't have to.
            prompt = "\n".join([ f"<|{m.role}|>\n{m.content}" for m in chain ])
            output = "".join([ck.content for ck in chunks ])
            c = self.dbc.completion.create(
                prompt,
                [completion.CompletionOutput(output, "unknown", None)],
                msg.opts,
                model,
                sha,
                tokenize_ms=-1,
                generation_ms=gen,
                queue_ms=queue,
                input_tokens=-1,
                output_tokens=-1,
            )

            # Finalize the messages and yield
            fmsg = self.dbc.message.finalize(msg.id)
            freply = self.dbc.message.finalize(reply.id, output, c.id)
            fmsg = dataclasses.replace(fmsg, children=[freply])
            yield json.dumps(fmsg, cls=util.CustomEncoder) + "\n"

        return Response(stream(), mimetype="application/jsonl")

    def message(self, id: str):
        token = self.authn()
        message = self.dbc.message.get(id, labels_for=token.client)
        if message is None:
            raise exceptions.NotFound()
        return jsonify(message)

    def delete_message(self, id: str):
        token = self.authn()
        message = self.dbc.message.get(id)
        if message is None:
            raise exceptions.NotFound()
        if message.creator != token.client:
            raise exceptions.Forbidden()
        return jsonify(self.dbc.message.delete(id, labels_for=token.client))

    def messages(self):
        token = self.authn()

        try:
            offset = int(request.args.get("offset", 0))
        except ValueError as e:
            raise exceptions.BadRequest(f"invalid offset: {e}")
        if offset < 0:
            raise exceptions.BadRequest("invalid offset: must be >= 0")

        try:
            limit = int(request.args.get("limit", 10))
        except ValueError as e:
            raise exceptions.BadRequest(f"invalid limit: {e}")
        if limit < 0:
            raise exceptions.BadRequest("invalid limit: must be >= 0")
        if limit > 100:
            raise exceptions.BadRequest("invalid limit: must be <= 100")

        try:
            return jsonify(self.dbc.message.list(
                labels_for=token.client,
                creator=request.args.get("creator"),
                deleted="deleted" in request.args,
                opts=message.MessageListOpts(offset, limit),
            ))
        except message.OffsetOverflowError as e:
            raise exceptions.BadRequest(str(e))

    def schema(self):
        self.authn()
        return jsonify({
            "Message": {
                "InferenceOpts": message.InferenceOpts.schema()
            }
        })

    def create_label(self):
        token = self.authn()
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
            creator=token.client
        )
        if len(existing) > 0:
            raise exceptions.UnprocessableEntity(f"message {mid} already has label {existing[0].id}")
        lbl = self.dbc.label.create(msg.id, rating, token.client, request.json.get("comment"))
        return jsonify(lbl)

    def label(self, id: str):
        self.authn()
        label = self.dbc.label.get(id)
        if label is None:
            raise exceptions.NotFound()
        return jsonify(label)

    def labels(self):
        self.authn()
        return jsonify(self.dbc.label.list(
            request.args.get("message"),
            request.args.get("creator"),
            "deleted" in request.args
        ))

    def delete_label(self, id: str):
        token = self.authn()
        label = self.dbc.label.get(id)
        if label is None:
            raise exceptions.NotFound()
        if label.creator != token.client:
            raise exceptions.Forbidden()
        return jsonify(self.dbc.label.delete(id))

    def completions(self):
        self.authn()
        return jsonify(self.dbc.completion.list())

    def data_search(self):
        self.authn()

        query = request.args.get("query", default="", type=lambda s: s.strip())
        if query == "":
            raise exceptions.BadRequest("empty query")

        try:
            size = int(request.args.get("size", "10"))
        except ValueError as e:
            raise exceptions.BadRequest(f"invalid size: {e}")
        if size < 0:
            raise exceptions.BadRequest("size must be positive")
        if size > 100:
            raise exceptions.BadRequest("size > 100 not supported")

        try:
            offset = int(request.args.get("offset", "0"))
        except ValueError as e:
            raise exceptions.BadRequest(f"invalid from: {e}")
        if offset < 0:
            raise exceptions.BadRequest("offset must be positive")
        if offset > 10_000 - size:
            raise exceptions.BadRequest(f"max offset is {10_000-size}")

        filters = None
        sources = request.args.getlist("source", type=lambda s: s.strip())
        if len(sources) > 0:
            filters = dsearch.Filters(sources)

        return jsonify(self.didx.search(query, size, offset, filters))

    def data_doc(self, id: str):
        self.authn()
        doc = self.didx.doc(id)
        if doc is None:
            raise exceptions.NotFound()
        return jsonify(doc)

    def data_meta(self):
        self.authn()
        return jsonify({ "count": self.didx.doc_count() })

