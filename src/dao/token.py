from typing import Optional, Self, Tuple
from psycopg_pool import ConnectionPool
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import StrEnum

import secrets

class TokenType(StrEnum):
    """
    Tokens types dictate how they can be used:
    - A "client" token is used for authenticating API clients.
    - A "login" token is used for generating a "client" token using a URL.
    """
    Client = "client"
    Login = "login"

@dataclass
class Token:
    token: str
    client: str
    created: datetime
    expires: datetime
    token_type: TokenType
    creator: Optional[str] = None

    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires

    @classmethod
    def from_row(cls, d: Tuple[str, str, datetime, datetime, str, Optional[str]]) -> Self:
        return cls(d[0], d[1], d[2], d[3], TokenType(d[4]), d[5])

class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(
        self,
        client: str,
        token_type: TokenType = TokenType.Login,
        expires_in: Optional[timedelta] = None,
        creator: Optional[str] = None
    ) -> Token:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                token = secrets.token_urlsafe(32)
                expires = datetime.now(timezone.utc) + expires_in if expires_in is not None else None
                row = cur.execute(
                    """
                        INSERT INTO
                            client_token (token, client, expires, token_type, creator)
                        VALUES
                            (%s, %s, %s, %s, %s)
                        RETURNING
                            token, client, created, expires, token_type, creator
                    """,
                    (token, client, expires, token_type, creator)
                ).fetchone()
                assert row is not None
                return Token.from_row(row)

    def get(self, token: str, token_type: TokenType) -> Optional[Token]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                row = cur.execute(
                    """
                        SELECT
                            token, client, created, expires, token_type, creator
                        FROM
                            client_token
                        WHERE
                            token = %s
                        AND
                            token_type = %s
                    """,
                    (token, token_type)
                ).fetchone()
                return Token.from_row(row) if row is not None else None

    def expire(self, token: Token) -> Optional[Token]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                row = cur.execute(
                    """
                        UPDATE
                            client_token
                        SET expires = NOW()
                            WHERE token = %s
                        RETURNING token, client, created, expires, token_type, creator
                    """,
                    (token.token,)
                ).fetchone()
                return Token.from_row(row) if row is not None else None

