from datetime import datetime
from psycopg_pool import ConnectionPool
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional
from werkzeug import exceptions
from .. import obj
from . import paged

class Rating(IntEnum):
    FLAG = -1
    NEGATIVE = 0
    POSITIVE = 1

LabelRow = tuple[str, str, int, str, Optional[str], datetime, Optional[datetime]]

@dataclass
class Label:
    id: obj.ID
    message: str
    rating: Rating
    creator: str
    comment: Optional[str]
    created: datetime
    deleted: Optional[datetime]

    @staticmethod
    def from_row(row: LabelRow) -> 'Label':
        id, message, rating, creator, comment, created, deleted = row
        return Label(
            id,
            message,
            Rating(rating),
            creator,
            comment,
            created,
            deleted
        )

@dataclass
class LabelsList(paged.List):
    labels: list[Label]

class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(self, message: str, rating: Rating, creator: str, comment: Optional[str]) -> Label:
        if comment is not None and comment.strip() == "":
            raise exceptions.BadRequest("comment cannot be empty")
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    INSERT INTO
                        label (id, message, rating, creator, comment)
                    VALUES
                        (%s, %s, %s, %s, %s)
                    RETURNING
                        id, message, rating, creator, comment, created, deleted
                """
                values = (
                    obj.NewID("lbl"),
                    message,
                    rating,
                    creator,
                    comment.strip() if comment is not None else None
                )
                row = cur.execute(q, values).fetchone()
                if row is None:
                    raise RuntimeError("failed to create label")
                return Label.from_row(row)

    def get(self, id: str) -> Optional[Label]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    SELECT
                        id, message, rating, creator, comment, created, deleted
                    FROM
                        label
                    WHERE
                        id = %s
                """
                row = cur.execute(q, (id,)).fetchone()
                return Label.from_row(row) if row is not None else None

    def list(
        self,
        message: Optional[str] = None,
        creator: Optional[str] = None,
        deleted: bool = False,
        rating: Optional[Rating] = None,
        opts: paged.Opts = paged.Opts()
    ) -> LabelsList:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                allowed = set(["created"])
                field = opts.sort.field if opts.sort is not None else "created"
                if field not in allowed:
                    raise ValueError(f"invalid sort field: {field}")
                dir = opts.sort.direction.value if opts.sort is not None else paged.SortDirection.DESC.value
                q = f"""
                    SELECT
                        id, message, rating, creator, comment, created, deleted,
                        COUNT(*) OVER() AS total
                    FROM
                        label
                    WHERE
                        (message = %s OR %s)
                    AND
                        (creator = %s OR %s)
                    AND
                        (deleted IS NULL OR %s)
                    AND
                        (rating = %s OR %s)
                    ORDER BY
                        {field} {dir},
                        id
                    OFFSET %s
                    LIMIT %s
                """
                values = (
                    message,
                    message is None,
                    creator,
                    creator is None,
                    deleted,
                    rating,
                    rating is None,
                    opts.offset,
                    opts.limit
                )
                rows = cur.execute(q, values).fetchall() # type: ignore
                total = rows[0][7] if len(rows) > 0 else 0
                labels = [Label.from_row(row[:7]) for row in rows]
                meta = paged.ListMeta(total, opts.offset, opts.limit, paged.Sort(field, paged.SortDirection(dir)))
                return LabelsList(meta, labels)

    def delete(self, id: str) -> Optional[Label]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    UPDATE
                        label
                    SET
                        deleted = COALESCE(deleted, NOW())
                    WHERE
                        id = %s
                    RETURNING
                        id, message, rating, creator, comment, created, deleted
                """
                row = cur.execute(q, (id,)).fetchone()
                return Label.from_row(row) if row is not None else None

