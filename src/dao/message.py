import re
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Any, cast

import bs4
from psycopg import errors
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel
from pydantic import Field as PydanticField
from werkzeug import exceptions

from src import obj
from src.config.Model import ModelType

from . import label, paged


class Role(StrEnum):
    User = "user"
    Assistant = "assistant"
    System = "system"


@dataclass
class Field:
    name: str
    default: Any
    min: Any
    max: Any
    step: int | float | None = None


max_tokens = Field("max_tokens", 2048, 1, 2048, 1)
temperature = Field("temperature", 0.7, 0.0, 1.0, 0.01)
# n has a max of 1 when streaming. if we allow for non-streaming requests we can go up to 50
num = Field("n", 1, 1, 1, 1)
top_p = Field("top_p", 1.0, 0.01, 1.0, 0.01)
logprobs = Field("logprobs", None, 0, 10, 1)
stop = Field("stop", None, None, None)


class InferenceOpts(BaseModel):
    max_tokens: int = PydanticField(
        default=max_tokens.default,
        ge=max_tokens.min,
        le=max_tokens.max,
        multiple_of=max_tokens.step,
        strict=True,
    )
    temperature: float = PydanticField(
        default=temperature.default,
        ge=temperature.min,
        le=temperature.max,
        multiple_of=temperature.step,
        strict=True,
    )
    n: int = PydanticField(default=num.default, ge=num.min, le=num.max, multiple_of=num.step, strict=True)
    top_p: float = PydanticField(
        default=top_p.default,
        ge=top_p.min,
        le=top_p.max,
        multiple_of=top_p.step,
        strict=True,
    )
    logprobs: int | None = PydanticField(
        default=logprobs.default,
        ge=logprobs.min,
        le=logprobs.max,
        multiple_of=logprobs.step,
        strict=True,
    )
    stop: list[str] | None = PydanticField(default=stop.default)

    @staticmethod
    def opts_schema() -> dict[str, Field]:
        return {f.name: f for f in [max_tokens, temperature, num, top_p, logprobs, stop]}

    @staticmethod
    def from_request(request_opts: dict[str, Any]) -> "InferenceOpts":
        return InferenceOpts(**request_opts)


@dataclass
class TokenLogProbs:
    token_id: int
    text: str
    logprob: float


def prepare_logprobs(
    logprobs: list[list[TokenLogProbs]] | None,
) -> list[Jsonb] | None:
    if logprobs is None:
        return None
    # TODO: logprobs is a JSONB[] field now, but should probably be JSONB[][]; though this only
    # matters if we decide we want to query by index, which seems unlikely.
    return [Jsonb([asdict(lp) for lp in lps]) for lps in logprobs]


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
    # Label fields
    str | None,
    str | None,
    int | None,
    str | None,
    str | None,
    datetime | None,
    datetime | None,
]

MessagesByID = dict[str, "Message"]


@dataclass
class MessageChunk:
    message: obj.ID
    content: str
    logprobs: list[list[TokenLogProbs]] | None = None


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
        label_row = 22
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
        root: str | None = None,
        parent: str | None = None,
        template: str | None = None,
        logprobs: list[list[TokenLogProbs]] | None = None,
        completion: obj.ID | None = None,
        final: bool = True,
        original: str | None = None,
        private: bool = False,
        model_type: ModelType | None = None,
        finish_reason: str | None = None,
        harmful: bool | None = None,
        expiration_time: datetime | None = None,
        file_urls: list[str] | None = None,
    ) -> Message:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                try:
                    q = """
                        INSERT INTO
                            message (id, content, creator, role, opts, root, parent, template, logprobs, completion, final, original, private, model_type, finish_reason, harmful, model_id, model_host, expiration_time, file_urls)
                        VALUES
                            (%(id)s, %(content)s, %(creator)s, %(role)s, %(opts)s, %(root)s, %(parent)s, %(template)s, %(logprobs)s, %(completion)s, %(final)s, %(original)s, %(private)s, %(model_type)s, %(finish_reason)s, %(harmful)s, %(model_id)s, %(model_host)s, %(expiration_time)s, %(file_urls)s)
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
                            expiration_time,
                            file_urls,
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
                            "opts": Jsonb(opts.model_dump()),
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
                            "expiration_time": expiration_time,
                            "file_urls": file_urls,
                        },
                    ).fetchone()

                    if row is None:
                        msg = "failed to create message"
                        raise RuntimeError(msg)
                    return Message.from_row(row)
                except errors.ForeignKeyViolation as e:
                    # TODO: the dao probably shouldn't throw HTTP exceptions, instead it should
                    # throw something more generic that the server translates
                    match e.diag.constraint_name:
                        case "message_completion_fkey":
                            msg = f'completion "{completion}" not found'
                            raise exceptions.BadRequest(msg)
                        case "message_original_fkey":
                            msg = f'original "{original}" not found'
                            raise exceptions.BadRequest(msg)
                        case "message_parent_fkey":
                            msg = f'parent "{parent}" not found'
                            raise exceptions.BadRequest(msg)
                        case "message_root_fkey":
                            msg = f'root "{root}" not found'
                            raise exceptions.BadRequest(msg)
                        case "message_template_fkey":
                            msg = f'template "{template}" not found'
                            raise exceptions.BadRequest(msg)
                    msg = f"unknown foreign key violation: {e.diag.constraint_name}"
                    raise exceptions.BadRequest(msg)

    def get(self, id: str, agent: str | None = None) -> Message | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
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
                        message.expiration_time,
                        message.file_urls,
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
                    AND
                        (expiration_time IS NULL OR expiration_time > CURRENT_TIMESTAMP)
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
            _, msgs = Message.tree(Message.group_by_id([Message.from_row(r) for r in rows]))
            return msgs.get(id)

    def get_by_root(self, id: str) -> list[Message]:
        with self.pool.connection() as conn, conn.cursor() as cur:
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
                        message.expiration_time,
                        message.file_urls,
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
        content: str | None = None,
        logprobs: list[list[TokenLogProbs]] | None = None,
        completion: obj.ID | None = None,
        finish_reason: str | None = None,
        harmful: bool | None = None,
        file_urls: list[str] | None = None,
    ) -> Message | None:
        """
        Used to finalize a Message produced via a streaming response.
        """
        with self.pool.connection() as conn, conn.cursor() as cur:
            try:
                q = """
                        UPDATE
                            message
                        SET
                            content = COALESCE(%(content)s, content),
                            logprobs = COALESCE(%(logprobs)s, logprobs),
                            completion = COALESCE(%(completion)s, completion),
                            finish_reason = COALESCE(%(finish_reason)s, finish_reason),
                            harmful = COALESCE(%(harmful)s, harmful),
                            file_urls= COALESCE(%(file_urls)s, file_urls),
                            final = true
                        WHERE
                            id = %(id)s
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
                            expiration_time,
                            file_urls,
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
                    {
                        "content": content,
                        "logprobs": prepare_logprobs(logprobs),
                        "completion": completion,
                        "finish_reason": finish_reason,
                        "harmful": harmful,
                        "file_urls": file_urls,
                        "id": id,
                    },
                ).fetchone()
                return Message.from_row(row) if row is not None else None
            except errors.ForeignKeyViolation as e:
                match e.diag.constraint_name:
                    case "message_completion_fkey":
                        msg = f'completion "{completion}" not found'
                        raise exceptions.BadRequest(msg)
                msg = f"unknown foreign key violation: {e.diag.constraint_name}"
                raise exceptions.BadRequest(msg)

    def delete(self, id: str, agent: str | None = None) -> Message | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
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
                        updated.expiration_time,
                        updated.file_urls,
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

        with self.pool.connection() as conn, conn.cursor() as cursor:
            q = """
                    DELETE
                    FROM
                        message
                    WHERE id = ANY(%s)
                """
            cursor.execute(q, (ids,))

    def get_by_creator(self, creator: str) -> list[Message]:
        with self.pool.connection() as conn, conn.cursor() as cur:
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
                    message.expiration_time,
                    message.file_urls,
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
                    (message.creator = %(creator)s OR %(creator)s IS NULL)
                """
            
            rows = cur.execute(q, { "creator": creator }).fetchall()

            msg_list = list(map(Message.from_row, rows))

            return msg_list

    # TODO: allow listing non-final messages
    def get_list(
        self,
        creator: str | None = None,
        deleted: bool = False,
        opts: paged.Opts = paged.Opts(),
        agent: str | None = None,
    ) -> MessageList:
        """
        Returns messages from the database. If agent is set, both private messages
        and labels belonging to that user will be returned.
        """
        # TODO: add sort support for messages
        if opts.sort is not None:
            msg = "sorting messages is not supported"
            raise NotImplementedError(msg)
        with self.pool.connection() as conn, conn.cursor() as cur:
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
                    AND
                        (expiration_time IS NULL OR expiration_time > CURRENT_TIMESTAMP)
                    ORDER BY
                        created DESC,
                        id
                """
            args: dict[str, Any] = {
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
                        message.expiration_time,
                        message.file_urls,
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
                    AND
                        (expiration_time IS NULL OR expiration_time > CURRENT_TIMESTAMP)
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
            tree_roots, _ = Message.tree(Message.group_by_id([Message.from_row(r[1:]) for r in rows]))

            return MessageList(
                messages=tree_roots,
                meta=paged.ListMeta(total, opts.offset, opts.limit),
            )

    def migrate_messages_to_new_user(self, previous_user_id: str, new_user_id: str):

        params = {
            "new_user_id": new_user_id,
            "previous_user_id": previous_user_id,
        }

        with self.pool.connection() as conn:
            ql = """
                UPDATE label
                SET creator = %(new_user_id)s
                WHERE creator = %(previous_user_id)s
                """
            
            qm = """
                UPDATE message
                SET creator = %(new_user_id)s, expiration_time = NULL, private = false
                WHERE creator = %(previous_user_id)s
                """
            
            with conn.cursor() as cur:
                cur.execute( query=ql, params=params )

                return cur.execute( query=qm, params=params ).rowcount
