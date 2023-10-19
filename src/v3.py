from flask import Blueprint, jsonify, request, Response, redirect, current_app
from werkzeug import exceptions
from werkzeug.wrappers import response
from datetime import timedelta
from inferd.msg.inferd_pb2_grpc import InferDStub
from inferd.msg.inferd_pb2 import InferRequest
from google.protobuf.struct_pb2 import Struct
from . import db, util, auth, dsearch, config, parse
from .dao import message, label, completion, token, datachip, paged
from typing import Optional
from urllib.parse import urlparse, urlunparse

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
        self.get("/login/skiff")(self.login_by_skiff)

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

        self.get("/completion/<string:id>")(self.completion)

        self.get("/data/search")(self.data_search)
        self.get("/data/doc/<string:id>")(self.data_doc)
        self.get("/data/meta")(self.data_meta)

        self.get("/invite/login")(self.login_by_invite_token)
        self.post("/invite/token")(self.create_invite_token)

        self.post("/datachip")(self.create_datachip)
        self.get("/datachip/<string:id>")(self.datachip)
        self.patch("/datachip/<string:id>")(self.patch_datachip)
        self.get("/datachips")(self.datachips)

    def request_agent(self) -> Optional[token.Token]:
        provided = request.cookies.get(
            "token",
            default=auth.token_from_request(request)
        )
        if provided is None:
            return None
        return self.dbc.token.get(provided, token.TokenType.Auth)

    def authn(self) -> token.Token:
        agent = self.request_agent()
        if agent is None or agent.expired():
            raise exceptions.Unauthorized()

        current_app.logger.info({
            "path": request.path,
            "message": f"authorized client {agent.client}",
            "client": agent.client,
            "created": agent.created,
            "expires": agent.expires,
        })

        return agent

    def set_auth_cookie(self, resp: Response | response.Response, token: token.Token) -> Response | response.Response:
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
        agent = self.request_agent()
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
        if self.request_agent() is not None:
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
            nt = self.dbc.token.create(resolved_invite.client, token.TokenType.Auth, timedelta(days=7),
                                       invite=resolved_invite.token)
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
        grantor = self.authn()
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

        invite = self.dbc.token.create(grantee, token.TokenType.Invite, expires_in, creator=grantor.client)

        path = current_app.url_for("v3.login_by_invite_token", token=invite.token)
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
        agent = self.authn()
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
        agent = self.authn()
        prompt = self.dbc.template.prompt(id)
        if prompt is None:
            raise exceptions.NotFound()
        if prompt.author != agent.client:
            raise exceptions.Forbidden()
        return jsonify(self.dbc.template.update_prompt(id, deleted=True))

    def create_prompt(self):
        agent = self.authn()
        if request.json is None:
            raise exceptions.BadRequest("missing JSON body")

        prompt = self.dbc.template.create_prompt(
            request.json.get("name"),
            request.json.get("content"),
            agent.client
        )
        return jsonify(prompt)

    def create_message(self):
        agent = self.authn()
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
            agent.client,
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


        @dataclasses.dataclass
        class ParsedMessage:
            content: parse.MessageContent
            role: message.Role

        # Find all of the datachips
        parsed_chain = [ ParsedMessage(content=parse.MessageContent(m.content), role=m.role) for m in chain ]
        chip_ids = [ dc.id for pm in parsed_chain for dc in pm.content.datachips ]
        db_chips = { dc.id: dc for dc in self.dbc.datachip.get(chip_ids) }

        # Replace the datachips in the message content
        for pm in parsed_chain:
            for cc in pm.content.datachips:
                dc = db_chips.get(cc.id)
                if dc is None:
                    raise exceptions.BadRequest(f"datachip {cc.id} not found")
                cc.tag.replace_with(dc.content)

        input = Struct()
        input.update({
            "messages": [ { "role": pm.role, "content": pm.content.html() } for pm in parsed_chain ],
            "opts": dataclasses.asdict(msg.opts),
        })

        model = request.json.get("model", "allenai/tulu2-70b-qlora-bf16")
        req = InferRequest(compute_source_id=model, input=input)

        # Create a message that will eventually capture the streamed response.
        # TODO: should handle exceptions mid-stream by deleting and/or finalizing the message
        reply = self.dbc.message.create(
            "",
            agent.client,
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
                chunks.append(message.MessageChunk(reply.id, resp.result.output["text"]))
                gen += resp.result.inference_time.ToMilliseconds()
                queue = resp.result.queue_time.ToMilliseconds()
                yield json.dumps(chunks[-1], cls=util.CustomEncoder) + "\n"

            # The generation is complete. Store it.
            # TODO: InferD should store this so that we don't have to.
            # TODO: capture InferD request input instead of our manifestion of the prompt format
            prompt = "\n".join([ f"<|{pm.role}|>\n{pm.content.html()}" for pm in parsed_chain ])
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
            if fmsg is None:
                err = RuntimeError(f"failed to finalize message {msg.id}")
                yield json.dumps(message.MessageStreamError(reply.id, str(err)), cls=util.CustomEncoder) + "\n"
                raise err
            freply = self.dbc.message.finalize(reply.id, output, c.id)
            if freply is None:
                err = RuntimeError(f"failed to finalize message {reply.id}")
                yield json.dumps(message.MessageStreamError(reply.id, str(err)), cls=util.CustomEncoder) + "\n"
                raise err
            fmsg = dataclasses.replace(fmsg, children=[freply])
            yield json.dumps(fmsg, cls=util.CustomEncoder) + "\n"

        return Response(stream(), mimetype="application/jsonl")

    def message(self, id: str):
        agent = self.authn()
        message = self.dbc.message.get(id, labels_for=agent.client)
        if message is None:
            raise exceptions.NotFound()
        return jsonify(message)

    def delete_message(self, id: str):
        agent = self.authn()
        message = self.dbc.message.get(id)
        if message is None:
            raise exceptions.NotFound()
        if message.creator != agent.client:
            raise exceptions.Forbidden()
        deleted = self.dbc.message.delete(id, labels_for=agent.client)
        if deleted is None:
            raise exceptions.NotFound()
        return jsonify(deleted)

    def messages(self):
        agent = self.authn()
        return jsonify(self.dbc.message.list(
            labels_for=agent.client,
            creator=request.args.get("creator"),
            deleted="deleted" in request.args,
            opts=paged.parse_opts_from_querystring(request)
        ))

    def schema(self):
        self.authn()
        return jsonify({
            "Message": {
                "InferenceOpts": message.InferenceOpts.schema()
            }
        })

    def create_label(self):
        agent = self.authn()
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
            creator=agent.client
        )
        if len(existing) > 0:
            raise exceptions.UnprocessableEntity(f"message {mid} already has label {existing[0].id}")
        lbl = self.dbc.label.create(msg.id, rating, agent.client, request.json.get("comment"))
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
        agent = self.authn()
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
        self.authn()
        c = self.dbc.completion.get(id)
        if c is None:
            raise exceptions.NotFound()
        return jsonify(c)

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

    def create_datachip(self):
        agent = self.authn()
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
        self.authn()
        chips = self.dbc.datachip.get([id])
        if len(chips) == 0:
            raise exceptions.NotFound()
        if len(chips) > 1:
            raise exceptions.InternalServerError("multiple chips with same ID")
        return jsonify(chips[0])

    def patch_datachip(self, id: str):
        agent = self.authn()
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
        self.authn()
        return jsonify(self.dbc.datachip.list_all(
            creator=request.args.get("creator"),
            deleted="deleted" in request.args,
            opts=paged.parse_opts_from_querystring(request)
        ))

