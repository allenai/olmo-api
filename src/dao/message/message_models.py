from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Any, cast

from src import obj
from src.api_interface import APIInterface
from src.dao import label, paged
from src.dao.engine_models.message import Message as SQLAMessage
from src.dao.engine_models.model_config import ModelType
from src.dao.message.inference_opts_model import InferenceOpts
from src.message.map_text_snippet import text_snippet


class ToolCall(APIInterface):
    tool_name: str
    args: str | dict[str, Any] | None = None
    tool_call_id: str


class Role(StrEnum):
    User = "user"
    Assistant = "assistant"
    System = "system"
    ToolResponse = "tool_call_result"


@dataclass
class TokenLogProbs:
    token_id: int
    text: str
    logprob: float


class MessageChunk(APIInterface):
    message: obj.ID
    content: str
    logprobs: list[list[TokenLogProbs]] | None = None


class MessageStreamError(APIInterface):
    message: obj.ID
    error: str
    reason: str


MessagesByID = dict[str, "Message"]


MessageRow = tuple[
    # Message fields
    str,
    str,
    str,
    Role,
    dict[str, Any],
    str,
    datetime,
    datetime | None,
    str | None,
    str | None,
    list[list[dict]] | None,
    str | None,
    bool,
    str | None,
    bool,
    ModelType | None,
    str | None,
    bool | None,
    str,
    str,
    datetime | None,
    list[str] | None,
    str | None,
    # Label fields
    str | None,
    str | None,
    int | None,
    str | None,
    str | None,
    datetime | None,
    datetime | None,
    # Tool call fields
    str | None,
    str | None,
    dict[str, Any] | None,
    str | None,
]


@dataclass
class Message:
    id: obj.ID
    content: str
    snippet: str
    creator: str
    role: Role
    opts: InferenceOpts
    root: str
    created: datetime
    model_id: str
    model_host: str
    deleted: datetime | None = None
    parent: str | None = None
    template: str | None = None
    logprobs: list[list[TokenLogProbs]] | None = None
    children: list["Message"] | None = None
    completion: str | None = None
    final: bool = False
    original: str | None = None
    private: bool = False
    model_type: ModelType | None = None
    finish_reason: str | None = None
    harmful: bool | None = None
    expiration_time: datetime | None = None
    labels: list[label.Label] = field(default_factory=list)
    file_urls: list[str] | None = None
    thinking: str | None = None

    def flatten(self) -> list["Message"]:
        if self.children is None:
            return [self]

        flat: list[Message] = [self]
        for c in self.children:
            flat += c.flatten()
        return flat

    @staticmethod
    def from_row(r: MessageRow) -> "Message":
        labels = []
        # If the label id is not None, unpack the label.
        label_row = 23
        if r[label_row] is not None:
            labels = [label.Label.from_row(cast(label.LabelRow, r[label_row:]))]

        logprobs = None
        if r[10] is not None:
            logprobs = []
            for lp in r[10]:
                logprobs.append([TokenLogProbs(**l) for l in lp])

        return Message(
            id=r[0],
            content=r[1],
            snippet=text_snippet(r[1]),
            creator=r[2],
            role=r[3],
            # this uses model_construct instead of the normal constructor because we want to skip validation when it's coming from the DB
            # since it was saved we trust the data already
            opts=InferenceOpts.model_construct(**r[4]),
            root=r[5],
            created=r[6],
            deleted=r[7],
            parent=r[8],
            template=r[9],
            logprobs=logprobs,
            children=None,
            completion=r[11],
            final=r[12],
            original=r[13],
            private=r[14],
            model_type=r[15],
            finish_reason=r[16],
            harmful=r[17],
            model_id=r[18],
            model_host=r[19],
            expiration_time=r[20],
            file_urls=r[21],
            thinking=r[22],
            labels=labels,
        )

    def merge(self, m: "Message") -> "Message":
        if self.id != m.id:
            msg = f"cannot merge messages with different ids: {self.id} != {m.id}"
            raise RuntimeError(msg)
        return replace(self, labels=self.labels + m.labels)

    @staticmethod
    def group_by_id(msgs: list["Message"]) -> dict[str, "Message"]:
        message_ids: dict[str, Message] = {}
        for message in msgs:
            if message.id in message_ids:
                message_ids[message.id] = message_ids[message.id].merge(message)
                continue
            message_ids[message.id] = message
        return message_ids

    @staticmethod
    def tree(msgs: MessagesByID) -> tuple[list["Message"], MessagesByID]:
        roots = []
        for m in msgs.values():
            if m.parent is None:
                roots.append(m)
                continue

            # This might happen if the parent was deleted and thus wasn't returned
            # in the set that was queried.
            if m.parent not in msgs:
                continue

            parent = msgs[m.parent]
            siblings = parent.children if parent.children is not None else []

            # Roots are sorted by the creation date, in descending order. The most
            # recent should come first. But children are sorted in ascending order.
            # This is because the only messages with > 1 children are those that are
            # generated by the model, and the creation order matches the model's selection
            # order -- the most probable come first.
            msgs[m.parent].children = sorted([*siblings, m], key=lambda x: x.created)

        return roots, msgs


@dataclass
class MessageList(paged.List):
    messages: list[Message]


@dataclass
class ThreadList:
    threads: Sequence[SQLAMessage] | Sequence[Message]
    meta: paged.ListMeta
