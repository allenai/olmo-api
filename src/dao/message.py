from psycopg_pool import ConnectionPool
from psycopg.types.json import Json
from psycopg import errors
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime
from typing import Optional, Any, cast
from enum import StrEnum
from werkzeug import exceptions
from .. import obj
from . import label

class OffsetOverflowError(RuntimeError):
    def __init__(self, offset: int, total: int):
        self.offset = offset
        self.total = total
        super().__init__(f"offset {offset} is >= than total {total}")

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

max_tokens = Field("max_tokens", 2048, 1, 4096, 1)
temperature = Field("temperature", 1.0, 0.0, 2.0, 0.01)
num = Field("n", 1, 1, 50, 1)
top_p = Field("top_p", 1.0, 0.0, 1.0, 0.01)
logprobs = Field("logprobs", 0, 0, 5, 1)
stop = Field("stop", [], None, None)

@dataclass
class InferenceOpts:
    max_tokens: int = max_tokens.default
    temperature: float = temperature.default
    n: int = num.default
    top_p: float = top_p.default
    logprobs: int = logprobs.default
    stop: list[str] = field(default_factory=list)

    @staticmethod
    def schema() -> dict[str, Field]:
        return {
            f.name: f for f in [
                max_tokens,
                temperature,
                num,
                top_p,
                logprobs,
                stop
            ]
        }

    @staticmethod
    def from_request(d: dict[str, Any]) -> 'InferenceOpts':
        mt = d.get(max_tokens.name, max_tokens.default)
        if not isinstance(mt, int):
            raise ValueError(f"max_tokens {mt} is not an integer")
        if mt > max_tokens.max or mt < max_tokens.min:
            raise ValueError(f"max_tokens {mt} is not in range [{max_tokens.min}, {max_tokens.max}]")

        temp = float(d.get(temperature.name, temperature.default))
        if temp > temperature.max or temp < temperature.min:
            raise ValueError(f"temperature {temp} is not in range [{temperature.min}, {temperature.max}]")

        n = d.get(num.name, num.default)
        if not isinstance(n, int):
            raise ValueError(f"num {n} is not an integer")
        if n > num.max or n < num.min:
            raise ValueError(f"num {n} is not in range [{num.min}, {num.max}]")

        tp = float(d.get(top_p.name, top_p.default))
        if tp > top_p.max or tp <= top_p.min:
            raise ValueError(f"top_p {tp} is not in range ({top_p.min}, {top_p.max}]")

        lp = d.get(logprobs.name, logprobs.default)
        if not isinstance(lp, int):
            raise ValueError(f"logprobs {lp} is not an integer")
        if lp > logprobs.max or lp < logprobs.min:
            raise ValueError(f"logprobs {lp} is not in range [{logprobs.min}, {logprobs.max}]")

        sw = d.get(stop.name, stop.default)
        if not isinstance(sw, list):
            raise ValueError(f"stop words {sw} is not a list")
        for w in sw:
            if not isinstance(w, str):
                raise ValueError(f"stop word {w} is not a string")

        return InferenceOpts(mt, temp, n, tp, lp, sw)

@dataclass
class LogProbs:
    # Candidate tokens, sorted by priority in descending order.
    candidates: list[tuple[str, float]]
    # The text offset for the token in the original completion.
    offset: int

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
    Optional[list[dict[str, Any]]],
    Optional[str],
    bool,
    Optional[str],

    # Label fields
    Optional[str],
    Optional[str],
    Optional[int],
    Optional[str],
    Optional[str],
    Optional[datetime],
    Optional[datetime]
]

MessagesByID = dict[str, 'Message']

@dataclass
class MessageChunk:
    message: obj.ID
    content: str

@dataclass
class Message:
    id: obj.ID
    content: str
    creator: str
    role: Role
    opts: InferenceOpts
    root: str
    created: datetime
    deleted: Optional[datetime] = None
    parent: Optional[str] = None
    template: Optional[str] = None
    # logprobs, if requested, is a list of LogProbs. Each entry provides
    # a list of candidate tokens and their log normalized probabilities, ordered
    # from the most to lease probable. The index of each item corresponds to the
    # associated output tokens' index.
    # TODO: list[T] instead of Optional[list[T]].
    logprobs: Optional[list[LogProbs]] = None
    children: Optional[list['Message']] = None
    completion: Optional[str] = None
    final: bool = False
    original: Optional[str] = None
    labels: list[label.Label] = field(default_factory=list)

    def flatten(self) -> list['Message']:
        if self.children is None:
            return [self]
        flat: list[Message] = [self]
        for c in self.children:
            flat += c.flatten()
        return flat

    @staticmethod
    def from_row(r: MessageRow) -> 'Message':
        labels = []
        # If the label id is not None, unpack the label.
        li = 14
        if r[li] is not None:
            labels = [label.Label.from_row(cast(label.LabelRow, r[li:]))]

        return Message(
            id=r[0],
            content=r[1],
            creator=r[2],
            role=r[3],
            opts=InferenceOpts(**r[4]),
            root=r[5],
            created=r[6],
            deleted=r[7],
            parent=r[8],
            template=r[9],
            logprobs=[LogProbs(**l) for l in r[10]] if r[10] is not None else None,
            children=None,
            completion=r[11],
            final=r[12],
            original=r[13],
            labels=labels,
        )

    def merge(self, m: 'Message') -> 'Message':
        assert self.id == m.id
        return replace(self, labels=self.labels + m.labels)

    @staticmethod
    def group_by_id(msgs: list['Message']) -> dict[str, 'Message']:
        mids = {}
        for m in msgs:
            if m.id in mids:
                mids[m.id] = mids[m.id].merge(m)
                continue
            mids[m.id] = m
        return mids

    @staticmethod
    def tree(msgs: MessagesByID) -> tuple[list['Message'], MessagesByID]:
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
class MessageListOpts:
    offset: Optional[int] = None
    limit: Optional[int] = None

@dataclass
class MessageListMeta:
    total: int
    offset: Optional[int] = None
    limit: Optional[int] = None

@dataclass
class MessageList:
    messages: list[Message]
    meta: MessageListMeta

class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(
        self,
        content: str,
        creator: str,
        role: Role,
        opts: InferenceOpts,
        root: Optional[str] = None,
        parent: Optional[str] = None,
        template: Optional[str] = None,
        logprobs: Optional[list[LogProbs]] = None,
        completion: Optional[obj.ID] = None,
        final: bool = True,
        original: Optional[str] = None
    ) -> Message:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                try:
                    q = """
                        INSERT INTO
                            message (id, content, creator, role, opts, root, parent, template, logprobs, completion, final, original)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    row = cur.execute(q, (
                        mid,
                        content,
                        creator,
                        role,
                        Json(asdict(opts)),
                        root or mid,
                        parent,
                        template,
                        [Json(asdict(lp)) for lp in logprobs] if logprobs is not None else None,
                        completion,
                        final,
                        original
                    )).fetchone()
                    assert row is not None
                    return(Message.from_row(row))
                except errors.ForeignKeyViolation as e:
                    # TODO: the dao probably shouldn't throw HTTP exceptions, instead it should
                    # throw something more generic that the server translates
                    match e.diag.constraint_name:
                        case "message_completion_fkey":
                            raise exceptions.BadRequest(f"completion \"{completion}\" not found")
                        case "message_original_fkey":
                            raise exceptions.BadRequest(f"original \"{original}\" not found")
                        case "message_parent_fkey":
                            raise exceptions.BadRequest(f"parent \"{parent}\" not found")
                        case "message_root_fkey":
                            raise exceptions.BadRequest(f"root \"{root}\" not found")
                        case "message_template_fkey":
                            raise exceptions.BadRequest(f"template \"{template}\" not found")
                    raise exceptions.BadRequest(f"unknown foreign key violation: {e.diag.constraint_name}")

    def get(self, id: str, labels_for: Optional[str] = None) -> Optional[Message]:
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
                rows = cur.execute(q, (labels_for, id,)).fetchall()
                _, msgs = Message.tree(Message.group_by_id([Message.from_row(r) for r in rows]))
                return msgs.get(id)

    def finalize(self, id: obj.ID, content: Optional[str] = None, completion: Optional[obj.ID] = None) -> Message:
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
                            completion = COALESCE(%s, completion),
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
                    row = cur.execute(q, (content, completion, id)).fetchone()
                    assert row is not None
                    return Message.from_row(row)
                except errors.ForeignKeyViolation as e:
                    match e.diag.constraint_name:
                        case "message_completion_fkey":
                            raise exceptions.BadRequest(f"completion \"{completion}\" not found")
                    raise exceptions.BadRequest(f"unknown foreign key violation: {e.diag.constraint_name}")


    def delete(self, id: str, labels_for: Optional[str] = None) -> Message:
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
                row = cur.execute(q, (id, labels_for)).fetchone()
                assert row is not None
                return Message.from_row(row)

    # TODO: allow listing non-final messages
    def list(
        self,
        labels_for: Optional[str] = None,
        creator: Optional[str] = None,
        deleted: bool = False,
        opts: MessageListOpts = MessageListOpts()
    ) -> MessageList:
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
                    ORDER BY
                        created DESC,
                        id
                """
                args = {
                    "creator": creator,
                    "deleted": deleted
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
                        label.creator = %(labels_for)s
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
                args["labels_for"] = labels_for

                rows = cur.execute(q, args).fetchall()

                # This should only happen in two circumstances:
                # 1. There's no messages
                # 2. The offset is greater than the number of root messages
                if len(rows) == 0:
                    args["offset"] = 0
                    row = cur.execute(q, args).fetchone()
                    total = row[0] if row is not None else 0
                    if opts.offset is not None and opts.offset >= total:
                        raise OffsetOverflowError(opts.offset, total)
                    return MessageList([], MessageListMeta(total, opts.offset, opts.limit))

                total = rows[0][0]
                roots, _ = Message.tree(Message.group_by_id([Message.from_row(r[1:]) for r in rows]))

                return MessageList(roots, MessageListMeta(total, opts.offset, opts.limit))
