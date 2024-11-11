import dataclasses
import json
import os
from datetime import datetime, timedelta, timezone
from time import time_ns
from typing import Generator, List, Optional

import grpc
from flask import current_app, request
from google.protobuf.struct_pb2 import Struct
from werkzeug import exceptions

from src import config, db, parse, util
from src.auth import token
from src.auth.auth_service import authn
from src.dao import completion, message
from src.inference.InferDEngine import InferDEngine
from src.inference.InferenceEngine import (
    FinishReason,
    InferenceEngine,
    InferenceEngineMessage,
)
from src.inference.ModalEngine import ModalEngine
from src.inference.TogetherAIEngine import TogetherAIEngine
from src.message.GoogleModerateText import GoogleModerateText
from src.message.SafetyChecker import (
    SafetyCheckRequest,
    SafetyCheckerType,
    SafetyChecker,
)
from src.message.WildGuard import WildGuard


def check_message_safety(
    text: str, checker_type: SafetyCheckerType = SafetyCheckerType.Google
) -> bool | None:
    safety_checker: SafetyChecker = GoogleModerateText()
    request = SafetyCheckRequest(text=text)

    if checker_type == SafetyCheckerType.WildGuard:
        safety_checker = WildGuard()

    try:
        result = safety_checker.check_request(request)

        return result.is_safe()

    except Exception as e:
        current_app.logger.error(
            "Skipped message safety check due to error: %s. ", repr(e)
        )

    return None


@dataclasses.dataclass
class ParsedMessage:
    content: parse.MessageContent
    role: message.Role


def get_engine(host: str) -> InferenceEngine:
    match host:
        case "inferd":
            return InferDEngine()
        case "modal":
            return ModalEngine()

        # here the engine is default to togetherAI
        case _:
            return TogetherAIEngine()


def create_message(
    dbc: db.Client, checker_type: SafetyCheckerType = SafetyCheckerType.Google
) -> message.Message | Generator[str, None, None]:

    start_all = time_ns()
    agent = authn()

    request = validate_and_map_create_message_request(dbc, agent=agent)

    inference_engine = get_engine(request.host)

    model = inference_engine.get_model_details(request.model_id)
    if not model:
        raise exceptions.BadRequest(
            f"model {request.model_id} is not available on {request.host}"
        )

    is_content_safe = None
    # Capture the SHA and logger, as the current_app context is lost in the generator.
    sha = os.environ["SHA"] if not current_app.debug else "DEV"
    logger = current_app.logger

    elapsed_safe = 0

    if request.role == message.Role.User:
        start_safe = time_ns()
        is_content_safe = check_message_safety(request.content, checker_type)
        elapsed_safe = (time_ns() - start_safe) // 1_000_000

        # We don't want to save messages from anonymous users
        # Not saving the completion is probably better than saving it with bad info
        if not agent.is_anonymous_user:
            dbc.completion.create(
                request.content,
                [
                    completion.CompletionOutput(
                        str(is_content_safe),
                        finish_reason=FinishReason.Stop,
                    )
                ],
                message.InferenceOpts(),
                checker_type,
                sha,
                tokenize_ms=-1,
                generation_ms=elapsed_safe,
                queue_ms=0,
                input_tokens=-1,
                output_tokens=-1,
            )

        if is_content_safe is False:
            raise exceptions.BadRequest(description="inappropriate_prompt")

    # We currently want anonymous users' messages to expire after 1 day
    message_expiration_time = (
        datetime.now(timezone.utc) + timedelta(days=1)
        if agent.is_anonymous_user
        else None
    )

    msg = dbc.message.create(
        request.content,
        agent.client,
        request.role,
        request.opts,
        model_id=request.model_id,
        model_host=request.host,
        root=request.parent.root if request.parent is not None else None,
        parent=request.parent.id if request.parent is not None else None,
        template=request.template,
        final=request.role == message.Role.Assistant,
        original=request.original,
        private=request.private,
        harmful=None if is_content_safe is None else not is_content_safe,
        expiration_time=message_expiration_time,
    )

    if msg.role == message.Role.Assistant:
        return msg

    # Resolve the message chain if we need to.
    chain = [msg]
    if request.root is not None:
        msgs = message.Message.group_by_id(request.root.flatten())
        while chain[-1].parent is not None:
            chain.append(msgs[chain[-1].parent])
        chain.reverse()

    # Find all of the datachips
    datachip_info = map_datachip_info(dbc, chain)

    input = Struct()
    input.update(
        {
            "messages": [dataclasses.asdict(datachip) for datachip in datachip_info],
            "opts": dataclasses.asdict(msg.opts),
        }
    )

    # Create a message that will eventually capture the streamed response.
    # TODO: should handle exceptions mid-stream by deleting and/or finalizing the message
    reply = dbc.message.create(
        "",
        agent.client,
        message.Role.Assistant,
        msg.opts,
        model_id=request.model_id,
        model_host=request.host,
        root=msg.root,
        parent=msg.id,
        final=False,
        private=request.private,
        model_type=model.model_type,
        expiration_time=message_expiration_time,
    )

    # Update the parent message to include the reply.
    msg = dataclasses.replace(msg, children=[reply])

    def stream() -> Generator[str, None, None]:
        # We keep track of each chunk and the timing information per-chunk
        # so that we can manifest a completion at the end. This will go
        # away when InferD stores this I/O.
        chunks: list[message.MessageChunk] = []
        start_gen = time_ns()

        # First yield the new user message
        yield format_message(msg)

        # Now yield each chunk as it's returned.
        finish_reason: Optional[FinishReason] = None
        try:
            first_ns = 0
            chunk_count = 0
            input_token_count = -1
            output_token_count = -1
            for chunk in inference_engine.create_streamed_message(
                model=model.compute_source_id,
                messages=datachip_info,
                inference_options=reply.opts,
            ):
                finish_reason = chunk.finish_reason

                logprobs = chunk.logprobs if chunk.logprobs is not None else []
                mapped_logprobs = [
                    [
                        message.TokenLogProbs(
                            token_id=lp.token_id, text=lp.text, logprob=lp.logprob
                        )
                        for lp in lp_list
                    ]
                    for lp_list in logprobs
                ]

                new_chunk = message.MessageChunk(
                    message=reply.id,
                    content=chunk.content,
                    logprobs=mapped_logprobs,
                )
                chunks.append(new_chunk)

                input_token_count = chunk.input_token_count
                output_token_count = chunk.output_token_count
                chunk_count += 1
                first_ns = time_ns() if first_ns == 0 else first_ns
                yield format_message(new_chunk)
        except grpc.RpcError as e:
            err = f"inference failed: {e}"
            yield format_message(
                message.MessageStreamError(reply.id, err, "grpc inference failed")
            )

        gen = time_ns() - start_gen
        gen = gen // 1_000_000

        match finish_reason:
            case FinishReason.UnclosedStream:
                err = "inference failed for an unknown reason: sometimes this happens when the prompt is too long"
                yield format_message(
                    message.MessageStreamError(reply.id, err, finish_reason)
                )

            case FinishReason.Length:
                err = "the conversation is too large for the model to process, please shorten the conversation and try again"
                yield format_message(
                    message.MessageStreamError(reply.id, err, finish_reason)
                )

            case FinishReason.Aborted:
                err = "inference aborted for an unknown reason"
                yield format_message(
                    message.MessageStreamError(reply.id, err, finish_reason)
                )

            case FinishReason.Stop:
                # This isn't an error
                pass

        # The generation is complete. Store it.
        # TODO: InferD should store this so that we don't have to.
        # TODO: capture InferD request input instead of our manifestation of the prompt format
        prompt = create_prompt_from_datachips(datachip_info)
        output, logprobs = create_output_from_chunks(chunks)

        messageCompletion = None
        if not agent.is_anonymous_user:
            messageCompletion = dbc.completion.create(
                prompt,
                [completion.CompletionOutput(output, finish_reason, logprobs)],
                msg.opts,
                model.compute_source_id,
                sha,
                tokenize_ms=-1,
                generation_ms=gen,
                queue_ms=0,
                input_tokens=input_token_count,
                output_tokens=output_token_count,
            )

        # Finalize the messages and yield
        finalMessage = dbc.message.finalize(msg.id)
        if finalMessage is None:
            err = RuntimeError(f"failed to finalize message {msg.id}")
            yield format_message(
                message.MessageStreamError(reply.id, str(err), "finalization failure")
            )
            raise err

        finalReply = dbc.message.finalize(
            reply.id,
            output,
            logprobs,
            messageCompletion.id if messageCompletion is not None else None,
            finish_reason,
        )
        if finalReply is None:
            err = RuntimeError(f"failed to finalize message {reply.id}")
            yield format_message(
                message.MessageStreamError(reply.id, str(err), "finalization failure")
            )
            raise err

        finalMessage = dataclasses.replace(finalMessage, children=[finalReply])

        end_all = time_ns()
        logger.info({
            "event":"inference.timing",
            "ttft_ms":(first_ns - start_all) // 1e+6,
            "total_ms":(end_all - start_all) // 1e+6,
            "safety_ms":elapsed_safe,
            "input_tokens":input_token_count,
            "output_tokens":output_token_count,
            "sha":sha,
            "model":model.id,
            "safety_check_id":checker_type,
        })
        yield format_message(finalMessage)

    return stream()


@dataclasses.dataclass
class CreateMessageRequest:
    parent: message.Message | None
    opts: message.InferenceOpts
    content: str
    role: message.Role
    original: str
    private: bool
    root: message.Message | None
    template: str
    model_id: str
    host: str


def validate_and_map_create_message_request(dbc: db.Client, agent: token.Token):
    if request.json is None:
        raise exceptions.BadRequest("no request body")

    pid = request.json.get("parent")
    parent = dbc.message.get(pid) if pid is not None else None
    if pid is not None and parent is None:
        raise exceptions.BadRequest(f"parent message {pid} not found")

    try:
        requestOpts = request.json.get("opts")
        opts = (
            message.InferenceOpts.from_request(requestOpts)
            if requestOpts is not None
            else message.InferenceOpts()
        )
    except ValueError as e:
        raise exceptions.BadRequest(str(e))

    if opts.n > 1:
        raise exceptions.BadRequest("n > 1 not supported when streaming")

    content: str = request.json.get("content")
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

    original: str = request.json.get("original")
    if original is not None and parent is not None and original == parent.id:
        raise exceptions.BadRequest("original message cannot be parent")

    # We don't currently allow anonymous users to share messages
    private: Optional[bool] = (
        False if agent.is_anonymous_user else request.json.get("private")
    )
    root = None
    template = request.json.get("template")

    if parent is not None:
        root = dbc.message.get(parent.root)
        if root is None:
            raise RuntimeError(f"root message {parent.root} not found")
        # Only the creator of a thread can create follow-up prompts
        if root.creator != agent.client:
            raise exceptions.Forbidden()
        # Transitively inherit the private status
        if private is None:
            private = root.private
        # Validate that visibility is the same for all messages in the thread
        if root.private != private:
            raise exceptions.BadRequest(
                "visibility must be identical for all messages in a thread"
            )
    elif private is None:
        private = False

    if not isinstance(private, bool):
        raise exceptions.BadRequest("private must be a boolean")

    host = request.json.get("host", config.model_hosts[0])
    model_id = request.json.get(
        "model", getattr(config.cfg, config.model_hosts[0]).default_model
    )

    return CreateMessageRequest(
        parent=parent,
        opts=opts,
        content=content,
        role=role,
        original=original,
        private=private,
        root=root,
        template=template,
        model_id=model_id,
        host=host,
    )


def map_datachip_info(
    dbc: db.Client, chain: list[message.Message]
) -> list[InferenceEngineMessage]:
    parsedMessages = [
        ParsedMessage(content=parse.MessageContent(message.content), role=message.role)
        for message in chain
    ]
    refs = [
        datachip.ref
        for parsedMessages in parsedMessages
        for datachip in parsedMessages.content.datachips
    ]
    chips = {
        datachip.ref: datachip.content
        for datachip in dbc.datachip.resolve(list(set(refs)))
    }

    datachips = [
        InferenceEngineMessage(
            role=pm.role, content=pm.content.replace_datachips(chips)
        )
        for pm in parsedMessages
    ]

    return datachips


def format_message(obj) -> str:
    return json.dumps(obj=obj, cls=util.CustomEncoder) + "\n"


def format_prompt(role: message.Role, content: str) -> str:
    return f"<|{role}|>\n{content}"


def create_prompt_from_datachips(datachips: List[InferenceEngineMessage]) -> str:
    return "\n".join(
        [format_prompt(datachip.role, datachip.content) for datachip in datachips]
    )


def create_output_from_chunks(chunks: List[message.MessageChunk]):
    output = ""
    logprobs: list[list[message.TokenLogProbs]] = []

    for chunk in chunks:
        output += chunk.content
        if chunk.logprobs is not None and len(chunk.logprobs) > 0:
            logprobs.append(*chunk.logprobs)

    return output, logprobs
