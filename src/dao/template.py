from datetime import datetime
from typing import Optional
from psycopg_pool import ConnectionPool
from dataclasses import dataclass
from werkzeug import exceptions
from .. import obj

@dataclass
class PromptTemplate:
    id: obj.ID
    name: str
    content: str
    author: str
    created: datetime
    updated: datetime
    deleted: Optional[datetime]

class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def prompts(self, deleted: bool = False) -> list[PromptTemplate]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
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
                return [PromptTemplate(*row) for row in cur.execute(q, (deleted,)).fetchall()]

    def create_prompt(self, name, content, author) -> PromptTemplate:
        if name.strip() == "":
            raise exceptions.BadRequest("name must not be empty")
        if content.strip() == "":
            raise exceptions.BadRequest("content must not be empty")
        if author.strip() == "":
            raise exceptions.BadRequest("author must not be empty")

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    INSERT INTO
                        prompt_template (id, name, content, author)
                    VALUES
                        (%s, %s, %s, %s)
                    RETURNING
                        id, name, content, author, created, updated, deleted
                """
                row = cur.execute(q, (obj.NewID("pt"), name, content, author)).fetchone()
                assert row is not None
                return PromptTemplate(*row)

    def prompt(self, id: str) -> Optional[PromptTemplate]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    SELECT
                        id, name, content, author, created, updated, deleted
                    FROM
                        prompt_template
                    WHERE
                        id = %s
                """
                row = cur.execute(q, (id,)).fetchone()
                return PromptTemplate(*row) if row is not None else None

    def update_prompt(self, id: str, name: Optional[str] = None, content: Optional[str] = None) -> PromptTemplate:
        if name is not None and name.strip() == "":
            raise exceptions.BadRequest("name must not be empty")
        if content is not None and content.strip() == "":
            raise exceptions.BadRequest("content must not be empty")

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    UPDATE
                        prompt_template
                    SET
                        name = COALESCE(%s, name),
                        content = COALESCE(%s, content),
                        updated = NOW()
                    WHERE
                        id = %s
                    RETURNING
                        id, name, content, author, created, updated, deleted
                """
                row = cur.execute(q, (name, content, id)).fetchone()
                assert row is not None
                return PromptTemplate(*row)

    def delete_prompt(self, id: str) -> PromptTemplate:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    UPDATE
                        prompt_template
                    SET
                        deleted = COALESCE(deleted, NOW()),
                        updated = COALESCE(deleted, NOW())
                    WHERE
                        id = %s
                    RETURNING
                        id, name, content, author, created, updated, deleted
                """
                row = cur.execute(q, (id,)).fetchone()
                assert row is not None
                return PromptTemplate(*row)


