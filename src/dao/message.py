import re
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Any, Optional, cast

import bs4
from psycopg import errors
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from werkzeug import exceptions

from .. import obj
from ..config import ModelType
from . import label, paged


class Role(StrEnum):
    User = "user"
    Assistant = "assistant"


@dataclass
class Field:
    name: str
    default: Any
    min: Any
    max: Any
    step: Optional[int | float] = None


max_tokens = Field("max_tokens", 2048, 1, 2048, 1)
temperature = Field("temperature", 0.7, 0.0, 2.0, 0.01)
num = Field("n", 1, 1, 50, 1)
top_p = Field("top_p", 1.0, 0.0, 1.0, 0.01)
logprobs = Field("logprobs", None, 0, 10, 1)
stop = Field("stop", None, None, None)


@dataclass
class InferenceOpts:
    max_tokens: int = max_tokens.default
    temperature: float = temperature.default
    n: int = num.default
    top_p: float = top_p.default
    logprobs: Optional[int] = logprobs.default
    stop: Optional[list[str]] = stop.default

    @staticmethod
    def schema() -> dict[str, Field]:
        return {
            f.name: f for f in [max_tokens, temperature, num, top_p, logprobs, stop]
        }

    @staticmethod
    def from_request(requestOpts: dict[str, Any]) -> "InferenceOpts":
        mt = requestOpts.get(max_tokens.name, max_tokens.default)
        if not isinstance(mt, int):
            raise ValueError(f"max_tokens {mt} is not an integer")
        if mt > max_tokens.max or mt < max_tokens.min:
            raise ValueError(
                f"max_tokens {mt} is not in range [{max_tokens.min}, {max_tokens.max}]"
            )

        temp = float(requestOpts.get(temperature.name, temperature.default))
        if temp > temperature.max or temp < temperature.min:
            raise ValueError(
                f"temperature {temp} is not in range [{temperature.min}, {temperature.max}]"
            )

        n = requestOpts.get(num.name, num.default)
        if not isinstance(n, int):
            raise ValueError(f"num {n} is not an integer")
        if n > num.max or n < num.min:
            raise ValueError(f"num {n} is not in range [{num.min}, {num.max}]")

        tp = float(requestOpts.get(top_p.name, top_p.default))
        if tp > top_p.max or tp < top_p.min:
            raise ValueError(f"top_p {tp} is not in range ({top_p.min}, {top_p.max}]")

        lp = requestOpts.get(logprobs.name, logprobs.default)
        if lp is not None:
            if not isinstance(lp, int):
                raise ValueError(f"logprobs {lp} is not an integer")
            if lp > logprobs.max or lp < logprobs.min:
                raise ValueError(
                    f"logprobs {lp} is not in range [{logprobs.min}, {logprobs.max}]"
                )

        sw = requestOpts.get(stop.name, stop.default)
        if sw is not None:
            if not isinstance(sw, list):
                raise ValueError(f"stop words {sw} is not a list")
            for w in sw:
                if not isinstance(w, str):
                    raise ValueError(f"stop word {w} is not a string")

        return InferenceOpts(mt, temp, n, tp, lp, sw)


@dataclass
class TokenLogProbs:
    token_id: int
    text: str
    logprob: float


def prepare_logprobs(
    logprobs: Optional[list[list[TokenLogProbs]]],
) -> Optional[list[Jsonb]]:
    if logprobs is None:
        return None
    # TODO: logprobs is a JSONB[] field now, but should probably be JSONB[][]; though this only
    # matters if we decide we want to query by index, which seems unlikely.
    return [Jsonb(list([asdict(lp) for lp in lps])) for lps in logprobs]


MessageRow = tuple[
    # Message fields
    str,
    str,
    str,
    Role,
    dict[str, Any],
    str,
    datetime,
    Optional[datetime],
    Optional[str],
    Optional[str],
    Optional[list[list[dict]]],
    Optional[str],
    bool,
    Optional[str],
    bool,
    Optional[ModelType],
    Optional[str],
    Optional[bool],
    str,
    str,
    # Label fields
    Optional[str],
    Optional[str],
    Optional[int],
    Optional[str],
    Optional[str],
    Optional[datetime],
    Optional[datetime],
]

MessagesByID = dict[str, "Message"]


@dataclass
class MessageChunk:
    message: obj.ID
    content: str
    logprobs: Optional[list[list[TokenLogProbs]]] = None


@dataclass
class MessageStreamError:
    message: obj.ID
    error: str
    reason: str


def first_n_words(s: str, n: int) -> str:
    # We take the first n * 32 characters as to avoid processing the entire text, which might be
    # large. This is for obvious reasons imperfect but probably good enough for manifesting a short,
    # representative snippet.
    words = re.split(r"\s+", s[: n * 32])
    return " ".join(words[:n]) + ("…" if len(words) > n else "")


def text_snippet(s: str) -> str:
    soup = bs4.BeautifulSoup(s, features="html.parser")
    return first_n_words(soup.get_text(), 16)


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
    deleted: Optional[datetime] = None
    parent: Optional[str] = None
    template: Optional[str] = None
    logprobs: Optional[list[list[TokenLogProbs]]] = None
    children: Optional[list["Message"]] = None
    completion: Optional[str] = None
    final: bool = False
    original: Optional[str] = None
    private: bool = False
    model_type: Optional[ModelType] = None
    finish_reason: Optional[str] = None
    harmful: Optional[bool] = None
    labels: list[label.Label] = field(default_factory=list)

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
        label_row = 20
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
            opts=InferenceOpts(**r[4]),
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
            labels=labels,
        )

    def merge(self, m: "Message") -> "Message":
        if self.id != m.id:
            raise RuntimeError(
                f"cannot merge messages with different ids: {self.id} != {m.id}"
            )
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
            msgs[m.parent].children = sorted(siblings + [m], key=lambda x: x.created)

        return roots, msgs


@dataclass
class MessageList(paged.List):
    messages: list[Message]


class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(
        self,
        content: str,
        creator: str,
        role: Role,
        opts: InferenceOpts,
        model_id: str,
        model_host: str,
        root: Optional[str] = None,
        parent: Optional[str] = None,
        template: Optional[str] = None,
        logprobs: Optional[list[list[TokenLogProbs]]] = None,
        completion: Optional[obj.ID] = None,
        final: bool = True,
        original: Optional[str] = None,
        private: bool = False,
        model_type: Optional[ModelType] = None,
        finish_reason: Optional[str] = None,
        harmful: Optional[bool] = None,
    ) -> Message:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                try:
                    q = """
                        INSERT INTO
                            message (id, content, creator, role, opts, root, parent, template, logprobs, completion, final, original, private, model_type, finish_reason, harmful, model_id, model_host)
                        VALUES
                            (%(id)s, %(content)s, %(creator)s, %(role)s, %(opts)s, %(root)s, %(parent)s, %(template)s, %(logprobs)s, %(completion)s, %(final)s, %(original)s, %(private)s, %(model_type)s, %(finish_reason)s, %(harmful)s, %(model_id)s, %(model_host)s)
                        RETURNING
                            id,
                            content,
                            creator,
                            role,
                            opts,
                            root,
                            created,
                            deleted,
                            parent,
                            template,
                            logprobs,
                            completion,
                            final,
                            original,
                            private,
                            model_type,
                            finish_reason,
                            harmful,
                            model_id,
                            model_host,
                            -- The trailing NULLs are for labels that wouldn't make sense to try
                            -- to JOIN. This simplifies the code for unpacking things.
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL
                    """
                    mid = obj.NewID("msg")
                    row = cur.execute(
                        q,
                        {
                            "id": mid,
                            "content": content,
                            "creator": creator,
                            "role": role,
                            "opts": Jsonb(asdict(opts)),
                            "root": root or mid,
                            "parent": parent,
                            "template": template,
                            "logprobs": prepare_logprobs(logprobs),
                            "completion": completion,
                            "final": final,
                            "original": original,
                            "private": private,
                            "model_type": model_type,
                            "finish_reason": finish_reason,
                            "harmful": harmful,
                            "model_id": model_id,
                            "model_host": model_host,
                        },
                    ).fetchone()
                    if row is None:
                        raise RuntimeError("failed to create message")
                    return Message.from_row(row)
                except errors.ForeignKeyViolation as e:
                    # TODO: the dao probably shouldn't throw HTTP exceptions, instead it should
                    # throw something more generic that the server translates
                    match e.diag.constraint_name:
                        case "message_completion_fkey":
                            raise exceptions.BadRequest(
                                f'completion "{completion}" not found'
                            )
                        case "message_original_fkey":
                            raise exceptions.BadRequest(
                                f'original "{original}" not found'
                            )
                        case "message_parent_fkey":
                            raise exceptions.BadRequest(f'parent "{parent}" not found')
                        case "message_root_fkey":
                            raise exceptions.BadRequest(f'root "{root}" not found')
                        case "message_template_fkey":
                            raise exceptions.BadRequest(
                                f'template "{template}" not found'
                            )
                    raise exceptions.BadRequest(
                        f"unknown foreign key violation: {e.diag.constraint_name}"
                    )

    def get(self, id: str, agent: Optional[str] = None) -> Optional[Message]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    SELECT
                        message.id,
                        message.content,
                        message.creator,
                        message.role,
                        message.opts,
                        message.root,
                        message.created,
                        message.deleted,
                        message.parent,
                        message.template,
                        message.logprobs,
                        message.completion,
                        message.final,
                        message.original,
                        message.private,
                        message.model_type,
                        message.finish_reason,
                        message.harmful,
                        message.model_id,
                        message.model_host,
                        label.id,
                        label.message,
                        label.rating,
                        label.creator,
                        label.comment,
                        label.created,
                        label.deleted
                    FROM
                        message
                    LEFT JOIN
                        label
                    ON
                        label.message = message.id
                    AND
                        label.creator = %s
                    AND
                        label.deleted IS NULL
                    WHERE
                        root = (SELECT root FROM message WHERE id = %s)
                    ORDER BY
                        message.created ASC
                """
                rows = cur.execute(
                    q,
                    (
                        agent,
                        id,
                    ),
                ).fetchall()
                _, msgs = Message.tree(
                    Message.group_by_id([Message.from_row(r) for r in rows])
                )
                return msgs.get(id)

    def get_by_root(self, id: str) -> list[Message]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    SELECT
                        message.id,
                        message.content,
                        message.creator,
                        message.role,
                        message.opts,
                        message.root,
                        message.created,
                        message.deleted,
                        message.parent,
                        message.template,
                        message.logprobs,
                        message.completion,
                        message.final,
                        message.original,
                        message.private,
                        message.model_type,
                        message.finish_reason,
                        message.harmful,
                        message.model_id,
                        message.model_host,
                        label.id,
                        label.message,
                        label.rating,
                        label.creator,
                        label.comment,
                        label.created,
                        label.deleted
                    FROM
                        message
                    LEFT JOIN
                        label
                    ON
                        label.message = message.id
                    WHERE
                        root = %s
                """
                rows = cur.execute(q, (id,)).fetchall()
                return [Message.from_row(r) for r in rows]

    def finalize(
        self,
        id: obj.ID,
        content: Optional[str] = None,
        logprobs: Optional[list[list[TokenLogProbs]]] = None,
        completion: Optional[obj.ID] = None,
        finish_reason: Optional[str] = None,
        harmful: Optional[bool] = None,
    ) -> Optional[Message]:
        """
        Used to finalize a Message produced via a streaming response.
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                try:
                    q = """
                        UPDATE
                            message
                        SET
                            content = COALESCE(%s, content),
                            logprobs = COALESCE(%s, logprobs),
                            completion = COALESCE(%s, completion),
                            finish_reason = COALESCE(%s, finish_reason),
                            harmful = COALESCE(%s, harmful),
                            final = true
                        WHERE
                            id = %s
                        RETURNING
                            id,
                            content,
                            creator,
                            role,
                            opts,
                            root,
                            created,
                            deleted,
                            parent,
                            template,
                            logprobs,
                            completion,
                            final,
                            original,
                            private,
                            model_type,
                            finish_reason,
                            harmful,
                            model_id,
                            model_host,
                            -- The trailing NULLs are for labels that wouldn't make sense to try
                            -- to JOIN. This simplifies the code for unpacking things.
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL
                    """
                    row = cur.execute(
                        q,
                        (
                            content,
                            prepare_logprobs(logprobs),
                            completion,
                            finish_reason,
                            harmful,
                            id,
                        ),
                    ).fetchone()
                    return Message.from_row(row) if row is not None else None
                except errors.ForeignKeyViolation as e:
                    match e.diag.constraint_name:
                        case "message_completion_fkey":
                            raise exceptions.BadRequest(
                                f'completion "{completion}" not found'
                            )
                    raise exceptions.BadRequest(
                        f"unknown foreign key violation: {e.diag.constraint_name}"
                    )

    def delete(self, id: str, agent: Optional[str] = None) -> Optional[Message]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    WITH updated AS (
                        UPDATE
                            message
                        SET
                            deleted = COALESCE(deleted, NOW())
                        WHERE
                            id = %s
                        RETURNING *
                    )
                    SELECT
                        updated.id,
                        updated.content,
                        updated.creator,
                        updated.role,
                        updated.opts,
                        updated.root,
                        updated.created,
                        updated.deleted,
                        updated.parent,
                        updated.template,
                        updated.logprobs,
                        updated.completion,
                        updated.final,
                        updated.original,
                        updated.private,
                        updated.model_type,
                        updated.finish_reason,
                        updated.harmful,
                        updated.model_id,
                        updated.model_host,
                        label.id,
                        label.message,
                        label.rating,
                        label.creator,
                        label.comment,
                        label.created,
                        label.deleted
                    FROM
                       updated
                    LEFT JOIN
                        label
                    ON
                        label.message = updated.id
                    AND
                        label.creator = %s
                    AND
                        label.deleted IS NULL

                """
                row = cur.execute(q, (id, agent)).fetchone()
                return Message.from_row(row) if row is not None else None

    def remove(self, ids: list[str]) -> None:
        if len(ids) == 0:
            return

        with self.pool.connection() as conn:
            with conn.cursor() as cursor:
                q = """
                    DELETE
                    FROM
                        message
                    WHERE id = ANY(%s)
                """
                cursor.execute(q, (ids,))

    # TODO: allow listing non-final messages
    def get_list(
        self,
        creator: Optional[str] = None,
        deleted: bool = False,
        opts: paged.Opts = paged.Opts(),
        agent: Optional[str] = None,
    ) -> MessageList:
        """
        Returns messages from the database. If agent is set, both private messages
        and labels belonging to that user will be returned.
        """
        # TODO: add sort support for messages
        if opts.sort is not None:
            raise NotImplementedError("sorting messages is not supported")
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                roots = """
                    SELECT
                        message.id,
                        COUNT(*) OVER() AS total
                    FROM
                        message
                    WHERE
                        (creator = %(creator)s OR %(creator)s IS NULL)
                    AND
                        (deleted IS NULL OR %(deleted)s)
                    AND
                        final = true
                    AND
                        parent IS NULL
                    AND
                        (private = false OR creator = %(agent)s)
                    ORDER BY
                        created DESC,
                        id
                """
                args = {
                    "creator": creator,
                    "deleted": deleted,
                    "agent": agent,
                }

                if opts.limit is not None:
                    roots += "\nLIMIT %(limit)s "
                    args["limit"] = opts.limit

                if opts.offset is not None:
                    roots += "\nOFFSET %(offset)s "
                    args["offset"] = opts.offset

                q = f"""
                    WITH root_ids AS ({roots})
                    SELECT
                        (SELECT total FROM root_ids LIMIT 1),
                        message.id,
                        message.content,
                        message.creator,
                        message.role,
                        message.opts,
                        message.root,
                        message.created,
                        message.deleted,
                        message.parent,
                        message.template,
                        message.logprobs,
                        message.completion,
                        message.final,
                        message.original,
                        message.private,
                        message.model_type,
                        message.finish_reason,
                        message.harmful,
                        message.model_id,
                        message.model_host,
                        label.id,
                        label.message,
                        label.rating,
                        label.creator,
                        label.comment,
                        label.created,
                        label.deleted
                    FROM
                        message
                    LEFT JOIN
                        label
                    ON
                        label.message = message.id
                    AND
                        label.creator = %(agent)s
                    AND
                        label.deleted IS NULL
                    WHERE
                        (message.creator = %(creator)s OR %(creator)s IS NULL)
                    AND
                        (message.deleted IS NULL OR %(deleted)s)
                    AND
                        message.final = true
                    AND
                        message.root IN (SELECT id FROM root_ids)
                    ORDER BY
                        message.created DESC,
                        message.id
                """
                args["agent"] = agent

                rows = cur.execute(q, args).fetchall()

                # This should only happen in two circumstances:
                # 1. There's no messages
                # 2. The offset is greater than the number of root messages
                if len(rows) == 0:
                    args["offset"] = 0
                    row = cur.execute(q, args).fetchone()
                    total = row[0] if row is not None else 0
                    return MessageList(
                        messages=[],
                        meta=paged.ListMeta(total, opts.offset, opts.limit, opts.sort),
                    )

                total = rows[0][0]
                roots, _ = Message.tree(
                    Message.group_by_id([Message.from_row(r[1:]) for r in rows])
                )

                return MessageList(
                    messages=roots, meta=paged.ListMeta(total, opts.offset, opts.limit)
                )
