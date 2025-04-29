import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg import errors
from psycopg_pool import ConnectionPool

from src import obj

from . import paged

DATACHIP_REF_DELIM = "/"

DatachipRef = str


def make_datachip_ref(creator: str, name: str) -> DatachipRef:
    return f"{creator}{DATACHIP_REF_DELIM}{name}"


class DuplicateDatachipRefError(ValueError):
    def __init__(self, ref: DatachipRef):
        super().__init__(f'datachip "{ref}" already exists')


@dataclass
class Datachip:
    id: str
    name: str
    ref: DatachipRef
    content: str
    creator: str
    created: datetime
    updated: datetime
    deleted: datetime | None = None


@dataclass
class Update:
    deleted: bool | None = None


@dataclass
class DatachipList(paged.List):
    datachips: list[Datachip]


def is_valid_datachip_name(name: str) -> bool:
    return re.match(r"^[a-zA-Z0-9_-]+$", name) is not None


class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def list_all(
        self,
        creator: str | None = None,
        deleted: bool = False,
        opts: paged.Opts = paged.Opts(),
    ) -> DatachipList:
        # TODO: add sort support for datachips
        if opts.sort is not None:
            msg = "sorting datachips is not supported"
            raise NotImplementedError(msg)
        with self.pool.connection() as conn, conn.cursor() as cur:
            q = """
                    SELECT
                        COUNT(*) OVER() AS total,
                        id,
                        name,
                        ref,
                        content,
                        creator,
                        created,
                        updated,
                        deleted
                    FROM
                        datachip
                    WHERE
                        (creator = %(creator)s OR %(creator)s IS NULL)
                    AND
                        (deleted IS NULL OR %(deleted)t)
                    ORDER BY
                        updated DESC,
                        created DESC,
                        name,
                        id
                    """
            args: dict[str, Any] = {"creator": creator, "deleted": deleted}

            if opts.offset is not None:
                q += "\nOFFSET %(offset)s "
                args["offset"] = opts.offset

            if opts.limit is not None:
                q += "\nLIMIT %(limit)s "
                args["limit"] = opts.limit

            rows = cur.execute(q, args).fetchall()

            # This should only happen in two circumstances:
            # 1. There's no chips
            # 2. The offset is greater than the number of chips
            if len(rows) == 0:
                args["offset"] = 0
                row = cur.execute(q, args).fetchone()
                total = row[0] if row is not None else 0
                return DatachipList(
                    datachips=[],
                    meta=paged.ListMeta(total, opts.offset, opts.limit),
                )

            total = rows[0][0]
            dc = [Datachip(*row[1:]) for row in rows]
            return DatachipList(datachips=dc, meta=paged.ListMeta(total, opts.offset, opts.limit))

    def create(self, name: str, content: str, creator: str) -> Datachip:
        if not is_valid_datachip_name(name):
            msg = f'invalid datachip name: "{name}", only alphanumeric characters and `_` or `-` are allowed'
            raise ValueError(msg)
        with self.pool.connection() as conn, conn.cursor() as cur:
            ref = make_datachip_ref(creator, name)
            try:
                cur.execute(
                    """
                            INSERT INTO datachip
                                (id, name, ref, content, creator)
                            VALUES
                                (%s, %s, %s, %s, %s)
                            RETURNING
                                id, name, ref, content, creator, created, updated
                        """,
                    (obj.NewID("dc"), name, ref, content, creator),
                )
                row = cur.fetchone()
                if row is None:
                    msg = "failed to create datachip"
                    raise RuntimeError(msg)
                return Datachip(*row)
            except errors.UniqueViolation:
                raise DuplicateDatachipRefError(ref)

    def get(self, ids: list[str]) -> list[Datachip]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                        SELECT
                            id,
                            name,
                            ref,
                            content,
                            creator,
                            created,
                            updated,
                            deleted
                        FROM
                            datachip
                        WHERE
                            id = ANY(%s)
                    """,
                (ids,),
            )
            return [Datachip(*row) for row in cur.fetchall()]

    def resolve(self, refs: list[DatachipRef]) -> list[Datachip]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                        SELECT
                            id,
                            name,
                            ref,
                            content,
                            creator,
                            created,
                            updated,
                            deleted
                        FROM
                            datachip
                        WHERE
                            ref = ANY(%s)
                    """,
                (refs,),
            )
            return [Datachip(*row) for row in cur.fetchall()]

    def update(self, id: str, up: Update) -> Datachip | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                        UPDATE
                            datachip
                        SET
                            deleted = {"NOW()" if up.deleted is True else "NULL" if up.deleted is False else "deleted"},
                            updated = {"NOW()" if up.deleted is not None else "updated"}
                        WHERE
                            id = %s
                        RETURNING
                            id, name, ref, content, creator, created, updated, deleted
                    """,
                (id,),
            )
            row = cur.fetchone()
            return Datachip(*row) if row is not None else None
