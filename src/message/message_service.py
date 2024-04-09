
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
from typing import Generator, List, Optional
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timezone
from enum import StrEnum
from src.log import logging_blueprint

import dataclasses
import os
import json
import io
import grpc

from src.message.output_part import FinishReason, OutputPart


@dataclasses.dataclass
class ParsedMessage:
    content: parse.MessageContent
    role: message.Role
    
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
    
        
def validate_and_map_request(dbc: db.Client, agent: token.Token, cfg: config.Config):
    if request.json is None:
        raise exceptions.BadRequest("no request body")

    pid = request.json.get("parent")
    parent = dbc.message.get(pid) if pid is not None else None
    if pid is not None and parent is None:
        raise exceptions.BadRequest(f"parent message {pid} not found")

    try:
        ropts = request.json.get("opts")
        opts = message.InferenceOpts.from_request(ropts) if ropts is not None else message.InferenceOpts()
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

    private: bool = request.json.get("private")
    root = None
    template = request.json.get("template")
    
    
    if parent is not None:
        root = dbc.message.get(parent.root)
        if root is None:
            raise RuntimeError(f"root message {parent.root} not found")
        # If a thread is private, only the creator can add to it. Otherwise
        # this could be used as a way to leak private messages to other users
        # by asking the LLM to emit the thread.
        if root.private and root.creator != agent.client:
            raise exceptions.Forbidden()
        # Transitively inherit the private status
        if private is None:
            private = root.private
        # Validate that visibility is the same for all messages in the thread
        if root.private != private:
            raise exceptions.BadRequest("visibility must be identical for all messages in a thread")
    elif private is None:
        private = False
        
    if not isinstance(private, bool):
        raise exceptions.BadRequest("private must be a boolean")

    model_id = request.json.get("model", cfg.inferd.default_model)

    
    return CreateMessageRequest(parent=parent, opts=opts, content=content, role=role, original=original, private=private, root=root, template=template, model_id=model_id)

   
def create_message(dbc: db.Client, cfg: config.Config, inferd: InferDStub):
    agent = authn(dbc)
    
    request = validate_and_map_request(dbc, agent=agent, cfg=cfg)
    
    msg = dbc.message.create(
        request.content,
        agent.client,
        request.role,
        request.opts,
        root=request.parent.root if request.parent is not None else None,
        parent=request.parent.id if request.parent is not None else None,
        template=request.template,
        final=request.role == message.Role.Assistant,
        original=request.original,
        private=request.private,
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
    input.update({
        "messages": [dataclasses.asdict(datachip) for datachip in datachip_info],
        "opts": dataclasses.asdict(msg.opts),
    })

    model = next((m for m in cfg.inferd.available_models if m.id == request.model_id), None)
    if not model:
        raise exceptions.BadRequest(f"model {request.model_id} not found")

    req = InferRequest(compute_source_id=model.compute_source_id, input=input)

    # Create a message that will eventually capture the streamed response.
    # TODO: should handle exceptions mid-stream by deleting and/or finalizing the message
    reply = dbc.message.create(
        "",
        agent.client,
        message.Role.Assistant,
        msg.opts,
        root=msg.root,
        parent=msg.id,
        final=False,
        private=request.private,
        model_type=model.model_type,
    )

    # Update the parent message to include the reply.
    msg = dataclasses.replace(msg, children=[reply])

    # Capture the SHA, as the current_app context is lost in the generator.
    sha = os.environ["SHA"] if not current_app.debug else "DEV"

    def stream() -> Generator[str, str, None]:
        # We keep track of each chunk and the timing information per-chunk
        # so that we can manifest a completion at the end. This will go
        # away when InferD stores this I/O.
        chunks: list[message.MessageChunk] = []
        gen, queue = 0, 0

        # First yield the new user message
        yield format_message(msg)

        # Now yield each chunk as it's returned.
        finish_reason: Optional[FinishReason] = None
        try:
            metadata = (("x-inferd-token", cfg.inferd.token),)
            for resp in inferd.Infer(req, metadata=metadata, wait_for_ready=True):
                part = OutputPart.from_struct(resp.result.output)
                finish_reason = part.finish_reason

                new_chunk = message.MessageChunk(
                    reply.id,
                    part.text,
                    part.logprobs if part.logprobs is not None else None)
                
                chunks.append(new_chunk)
                gen += resp.result.inference_time.ToMilliseconds()
                queue = resp.result.queue_time.ToMilliseconds()
                
                yield format_message(new_chunk)
                
        except grpc.RpcError as e:
            err = f"inference failed: {e}"
            yield format_message(message.MessageStreamError(reply.id, err))

        match finish_reason:
            case FinishReason.UnclosedStream:
                err = "inference failed for an unknown reason: sometimes this happens when the prompt is too long"
                yield format_message(message.MessageStreamError(reply.id, err))
                
            case FinishReason.Length:
                # If only one chunk was yielded and it's empty, it's probably because the prompt was too
                # long. Unfortunately we can't differentiate this from when the prompt stops because
                # max_tokens were generated, as vLLM doesn't distinguish the two.
                if len(chunks) == 1 and chunks[0] == "":
                    err = "the conversation is too large for the model to process, please shorten the conversation and try again"
                    yield format_message(message.MessageStreamError(reply.id, err))

            case FinishReason.Aborted:
                err = "inference aborted for an unknown reason"
                yield format_message(message.MessageStreamError(reply.id, err))
                
            case FinishReason.Stop:
                # This isn't an error
                pass

        # The generation is complete. Store it.
        # TODO: InferD should store this so that we don't have to.
        # TODO: capture InferD request input instead of our manifestation of the prompt format
        prompt = create_prompt_from_datachips(datachip_info)
        output, logprobs = create_output_from_chunks(chunks)
                
        messageCompletion = dbc.completion.create(
            prompt,
            [completion.CompletionOutput(output, "unknown", logprobs)],
            msg.opts,
            model.compute_source_id,
            sha,
            tokenize_ms=-1,
            generation_ms=gen,
            queue_ms=queue,
            input_tokens=-1,
            output_tokens=-1,
        )

        # Finalize the messages and yield
        finalMessage = dbc.message.finalize(msg.id)
        if finalMessage is None:
            err = RuntimeError(f"failed to finalize message {msg.id}")
            yield format_message(message.MessageStreamError(reply.id, str(err)))
            raise err

        finalReply = dbc.message.finalize(reply.id, output, logprobs, messageCompletion.id)
        if finalReply is None:
            err = RuntimeError(f"failed to finalize message {reply.id}")
            yield format_message(message.MessageStreamError(reply.id, str(err)))
            raise err
        
        finalMessage = dataclasses.replace(finalMessage, children=[finalReply])
        
        yield format_message(finalMessage)

    return stream()

@dataclasses.dataclass
class DatachipInfo:
    role: message.Role
    content: str
    
def map_datachip_info(dbc, chain)-> list[DatachipInfo]:
    parsedMessages = [ ParsedMessage(content=parse.MessageContent(message.content), role=message.role) for message in chain ]
    refs = [ datachip.ref for parsedMessages in parsedMessages for datachip in parsedMessages.content.datachips ]
    chips  = { datachip.ref: datachip.content for datachip in dbc.datachip.resolve(list(set(refs))) }
    
    datachips = [ DatachipInfo(role=pm.role, content=pm.content.replace_datachips(chips)) for pm in parsedMessages ]
    
    return datachips

def format_message(obj)-> str: 
    return json.dumps(obj=obj, cls=util.CustomEncoder) + "\n"

def format_prompt(role: message.Role, content: str) -> str: 
    return f"<|{role}|>\n{content}"

def create_prompt_from_datachips(datachips: List[DatachipInfo]) -> str:
    return "\n".join([ format_prompt(datachip.role, datachip.content) for datachip in datachips ])

def create_output_from_chunks(chunks: List[message.MessageChunk]):
    output = ""
    logprobs: list[list[message.TokenLogProbs]] = []
 
    for chunk in chunks:
        output += chunk.content
        if chunk.logprobs is not None:
            logprobs.append(*chunk.logprobs)
            
    return output, logprobs