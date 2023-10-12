from psycopg_pool import ConnectionPool
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from src import obj

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

class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def list(self, creator: Optional[str] = None, deleted: bool = False) -> list[Datachip]:
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
                            (creator = %(creator)s OR %(creator)s IS NULL)
                        AND
                            (deleted IS NULL OR %(deleted)t)
                        ORDER BY
                            updated DESC,
                            created DESC,
                            name,
                            id
                    """,
                    { "creator": creator, "deleted": deleted }
                )
                return [Datachip(*row) for row in cur.fetchall()]


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

    def get(self, id: str) -> Optional[Datachip]:
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
                            id = %s
                    """,
                    (id,)
                )
                row = cur.fetchone()
                return Datachip(*row) if row is not None else None

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

