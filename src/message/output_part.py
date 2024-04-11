import dataclasses
from typing import Optional

from google.protobuf import json_format
from google.protobuf.struct_pb2 import Struct

from src.dao import message


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
    def from_struct(cls, s: Struct) -> "OutputPart":
        op = json_format.MessageToDict(s)
        logprobs = (
            [
                [
                    message.TokenLogProbs(
                        int(lp["token_id"]), lp["text"], lp["logprob"]
                    )
                    for lp in lps
                ]
                for lps in op["logprobs"]
            ]
            if op.get("logprobs") is not None
            else None
        )
        fr = (
            FinishReason(op["finish_reason"])
            if op.get("finish_reason") is not None
            else None
        )
        token_ids = (
            [int(tid) for tid in op["token_ids"]]
            if op.get("token_ids") is not None
            else None
        )
        return cls(op["text"], token_ids, logprobs, fr)
