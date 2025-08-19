from dataclasses import asdict
from datetime import datetime
from typing import Any

from psycopg import errors
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from werkzeug import exceptions

from src import obj
from src.config.Model import ModelType
from src.dao import paged
from src.dao.message.message_models import InferenceOpts, Message, Role, ThreadList, TokenLogProbs


def prepare_logprobs(
    logprobs: list[list[TokenLogProbs]] | None,
) -> list[Jsonb] | None:
    if logprobs is None:
        return None
    # TODO: logprobs is a JSONB[] field now, but should probably be JSONB[][]; though this only
    # matters if we decide we want to query by index, which seems unlikely.
    return [Jsonb([asdict(lp) for lp in lps]) for lps in logprobs]


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
        thinking: str | None = None,
    ) -> Message:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                try:
                    q = """
                        INSERT INTO
                            message (id, content, creator, role, opts, root, parent, template, logprobs, completion, final, original, private, model_type, finish_reason, harmful, model_id, model_host, expiration_time, file_urls, thinking)
                        VALUES
                            (%(id)s, %(content)s, %(creator)s, %(role)s, %(opts)s, %(root)s, %(parent)s, %(template)s, %(logprobs)s, %(completion)s, %(final)s, %(original)s, %(private)s, %(model_type)s, %(finish_reason)s, %(harmful)s, %(model_id)s, %(model_host)s, %(expiration_time)s, %(file_urls)s, %(thinking)s)
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
                            thinking,
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
                            "thinking": thinking,
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
                        message.thinking,
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
                        message.thinking,
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
        thinking: str | None = None,
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
                            thinking = COALESCE(%(thinking)s, thinking),
 
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
                            thinking,
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
                        "thinking": thinking,
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
                        updated.thinking,
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
                    message.thinking,
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

            rows = cur.execute(q, {"creator": creator}).fetchall()

            msg_list = list(map(Message.from_row, rows))

            return msg_list

    # TODO: allow listing non-final messages
    def get_list(
        self,
        creator: str | None = None,
        deleted: bool = False,
        opts: paged.Opts = paged.Opts(),
        agent: str | None = None,
    ) -> "ThreadList":
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
                        message.thinking,
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
                return ThreadList(
                    threads=[],
                    meta=paged.ListMeta(total, opts.offset, opts.limit, opts.sort),
                )

            total = rows[0][0]
            tree_roots, _ = Message.tree(Message.group_by_id([Message.from_row(r[1:]) for r in rows]))

            return ThreadList(
                threads=tree_roots,
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
                cur.execute(query=ql, params=params)

                return cur.execute(query=qm, params=params).rowcount
