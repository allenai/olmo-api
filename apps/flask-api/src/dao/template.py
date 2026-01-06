from dataclasses import dataclass
from datetime import datetime

import core.object_id as obj
from psycopg_pool import ConnectionPool
from werkzeug import exceptions

PromptTemplateRow = tuple[str, str, str, str, datetime, datetime, datetime | None]


@dataclass
class PromptTemplate:
    id: obj.ID
    name: str
    content: str
    # deprecated: use creator
    author: str
    creator: str
    created: datetime
    updated: datetime
    deleted: datetime | None

    @classmethod
    def from_row(cls, row: PromptTemplateRow) -> "PromptTemplate":
        [id, name, content, author, created, updated, deleted] = row
        return cls(
            id=id,
            name=name,
            content=content,
            author=author,
            creator=author,
            created=created,
            updated=updated,
            deleted=deleted,
        )


class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def prompts(self, deleted: bool = False) -> list[PromptTemplate]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            q = """
                    SELECT
                        id, name, content, author, created, updated, deleted
                    FROM
                        prompt_template
                    WHERE
                        (deleted IS NULL OR %s)
                    ORDER BY
                        updated DESC,
                        created DESC,
                        name,
                        id
                """
            return [
                PromptTemplate.from_row(row)
                for row in cur.execute(q, (deleted,)).fetchall()
            ]

    def create_prompt(self, name, content, author) -> PromptTemplate:
        if name.strip() == "":
            msg = "name must not be empty"
            raise exceptions.BadRequest(msg)
        if content.strip() == "":
            msg = "content must not be empty"
            raise exceptions.BadRequest(msg)
        if author.strip() == "":
            msg = "author must not be empty"
            raise exceptions.BadRequest(msg)

        with self.pool.connection() as conn, conn.cursor() as cur:
            q = """
                    INSERT INTO
                        prompt_template (id, name, content, author)
                    VALUES
                        (%s, %s, %s, %s)
                    RETURNING
                        id, name, content, author, created, updated, deleted
                """
            row = cur.execute(q, (obj.NewID("pt"), name, content, author)).fetchone()
            if row is None:
                msg = "failed to create prompt template"
                raise RuntimeError(msg)
            return PromptTemplate.from_row(row)

    def prompt(self, id: str) -> PromptTemplate | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            q = """
                    SELECT
                        id, name, content, author, created, updated, deleted
                    FROM
                        prompt_template
                    WHERE
                        id = %s
                """
            row = cur.execute(q, (id,)).fetchone()
            return PromptTemplate.from_row(row) if row is not None else None

    def update_prompt(
        self,
        id: str,
        name: str | None = None,
        content: str | None = None,
        deleted: bool | None = None,
    ) -> PromptTemplate | None:
        if name is not None and name.strip() == "":
            msg = "name must not be empty"
            raise exceptions.BadRequest(msg)
        if content is not None and content.strip() == "":
            msg = "content must not be empty"
            raise exceptions.BadRequest(msg)

        with self.pool.connection() as conn, conn.cursor() as cur:
            q = f"""
                    UPDATE
                        prompt_template
                    SET
                        name = COALESCE(%s, name),
                        content = COALESCE(%s, content),
                        deleted = {"NOW()" if deleted is True else "NULL" if deleted is False else "deleted"},
                        updated = NOW()
                    WHERE
                        id = %s
                    RETURNING
                        id, name, content, author, created, updated, deleted
                """
            row = cur.execute(q, (name, content, id)).fetchone()
            return PromptTemplate.from_row(row) if row is not None else None
