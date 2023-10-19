from psycopg_pool import ConnectionPool
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .. import obj
from . import paged

@dataclass
class Datachip:
    id: str
    name: str
    content: str
    creator: str
    created: datetime
    updated: datetime
    deleted: Optional[datetime] = None

@dataclass
class Update:
    deleted: Optional[bool] = None

@dataclass
class DatachipList(paged.List):
    datachips: list[Datachip]

class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def list_all(
        self,
        creator: Optional[str] = None,
        deleted: bool = False,
        opts: paged.Opts = paged.Opts()
    ) -> DatachipList:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    SELECT
                        COUNT(*) OVER() AS total,
                        id,
                        name,
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
                args = { "creator": creator, "deleted": deleted }

                if opts.offset is not None:
                    q += "\nOFFSET %(offset)s "
                    args["offset"] = opts.offset

                print(opts)
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
                    return DatachipList(datachips=[], meta=paged.ListMeta(total, opts.offset, opts.limit))

                total = rows[0][0]
                dc = [Datachip(*row[1:]) for row in rows]
                return DatachipList(datachips=dc, meta=paged.ListMeta(total, opts.offset, opts.limit))

    def create(self, name: str, content: str, creator: str) -> Datachip:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                        INSERT INTO datachip
                            (id, name, content, creator)
                        VALUES
                            (%s, %s, %s, %s)
                        RETURNING
                            id, name, content, creator, created, updated
                    """,
                    (obj.NewID("dc"), name, content, creator)
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("failed to create datachip")
                return Datachip(*row)

    def get(self, ids: list[str]) -> list[Datachip]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT
                            id,
                            name,
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
                    (ids,)
                )
                return [Datachip(*row) for row in cur.fetchall()]

    def update(self, id: str, up: Update) -> Optional[Datachip]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                        UPDATE
                            datachip
                        SET
                            deleted = {"NOW()" if up.deleted == True else "NULL" if up.deleted == False else "deleted"},
                            updated = {"NOW()" if up.deleted is not None else "updated"}
                        WHERE
                            id = %s
                        RETURNING
                            id, name, content, creator, created, updated, deleted
                    """,
                    (id,)
                )
                row = cur.fetchone()
                return Datachip(*row) if row is not None else None

