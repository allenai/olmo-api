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
from typing import Optional
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timezone
from enum import StrEnum
from src.log import logging_blueprint

import dataclasses
import os
import json
import io
import grpc


class FinishReason(StrEnum):
    # Something caused the generation to be left incomplete. The only scenario where this happens
    # (that we know of) is when the prompt is too long and it's the only item being process (batch
    # size is 1):
    # See: https://github.com/allenai/inferd-tulu2/blob/main/src/svllm.py#L106
    UnclosedStream = "unclosed stream"

    # The model stopped because max_tokens was reached, or because the prompt was too long and
    # there were several items in the batch.
    Length = "length"

    # The model generated a response and stopped before max_tokens was reached.
    Stop = "stop"

    # The generation was aborted for an unknown reason.
    Aborted = "aborted"


@dataclasses.dataclass
class OutputPart:
    """
    An OutputPart is a single message part delivered from the Tulu2 model:
    https://github.com/allenai/inferd-tulu2/blob/main/src/svllm.py#L16-L20
    We also support the OLMo 7B model which currently only returns text:
    https://github.com/allenai/inferd-olmo/blob/b2aec55d942aee0a894fd080da50deed9e1f8440/src/model.py#L47-L47

    If we end up using other models via the same UI, we'll need to generalize.
    """
    text: str
    token_ids: Optional[list[int]]
    logprobs: Optional[list[list[message.TokenLogProbs]]] = None
    finish_reason: Optional[FinishReason] = None

    @classmethod
    def from_struct(cls, s: Struct) -> 'OutputPart':
        op = json_format.MessageToDict(s)
        logprobs = [
            [ message.TokenLogProbs(int(lp["token_id"]), lp["text"], lp["logprob"]) for lp in lps ] for lps in op["logprobs"]
        ] if op.get("logprobs") is not None else None
        fr = FinishReason(op["finish_reason"]) if op.get("finish_reason") is not None else None
        token_ids = [int(tid) for tid in op["token_ids"]] if op.get("token_ids") is not None else None
        return cls(op["text"], token_ids, logprobs, fr)