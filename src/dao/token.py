from typing import Optional
from psycopg_pool import ConnectionPool
from dataclasses import dataclass
from datetime import datetime

import secrets

@dataclass
class Token:
    token: str
    client: str
    created: datetime
    expires: datetime

class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(self, client: str) -> Token:
        token = secrets.token_urlsafe(32)
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                row = cur.execute(
                    """
                        INSERT INTO
                            client_token (token, client)
                        VALUES
                            (%s, %s)
                        RETURNING
                            token, client, created, expires
                    """,
                    (token, client)
                ).fetchone()
                assert row is not None
                return Token(*row)

    def get(self, token: str) -> Optional[Token]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                row = cur.execute(
                    """
                        SELECT
                            token, client, created, expires
                        FROM
                            client_token
                        WHERE
                            token = %s
                    """,
                    (token,)
                ).fetchone()
                return Token(*row) if row is not None else None
