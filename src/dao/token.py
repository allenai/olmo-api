from typing import Optional, Self, Tuple
from psycopg_pool import ConnectionPool
from psycopg import errors
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import StrEnum

import secrets

class DuplicateInviteError(Exception):
    def __init__(self, invite: str):
        super().__init__(f"invite {invite} was already used")

class TokenType(StrEnum):
    """
    Tokens types dictate how they can be used:
    - An "auth" token is used for authenticating API clients.
    - An "invite" token is used to create a "client" token by making a GET request to a URL.
    """
    Auth = "auth"
    Invite = "invite"

@dataclass
class Token:
    token: str
    client: str
    created: datetime
    expires: datetime
    token_type: TokenType
    creator: Optional[str] = None
    invite: Optional[str] = None

    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires

    @classmethod
    def from_row(cls, d: Tuple[str, str, datetime, datetime, str, Optional[str], Optional[str]]) -> Self:
        return cls(d[0], d[1], d[2], d[3], TokenType(d[4]), d[5], d[6])

class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(
        self,
        client: str,
        token_type: TokenType,
        expires_in: Optional[timedelta] = None,
        creator: Optional[str] = None,
        invite: Optional[str] = None
    ) -> Token:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                try:
                    token = secrets.token_urlsafe(32)
                    expires = datetime.now(timezone.utc) + expires_in if expires_in is not None else None
                    row = cur.execute(
                        """
                            INSERT INTO
                                client_token (token, client, expires, token_type, creator, invite)
                            VALUES
                                (%s, %s, %s, %s, %s, %s)
                            RETURNING
                                token, client, created, expires, token_type, creator, invite
                        """,
                        (token, client, expires, token_type, creator, invite)
                    ).fetchone()
                    assert row is not None
                    return Token.from_row(row)
                except errors.UniqueViolation as e:
                    if e.diag.constraint_name == "client_token_invite_key":
                        assert invite is not None
                        raise DuplicateInviteError(invite)
                    raise e

    def get(self, token: str, token_type: TokenType) -> Optional[Token]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                row = cur.execute(
                    """
                        SELECT
                            token, client, created, expires, token_type, creator, invite
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

    def expire(self, token: Token, token_type: TokenType) -> Optional[Token]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                row = cur.execute(
                    """
                        UPDATE
                            client_token
                        SET
                            expires = NOW()
                        WHERE
                            token = %s
                        AND
                            token_type = %s
                        RETURNING token, client, created, expires, token_type, creator, invite
                    """,
                    (token.token, token_type)
                ).fetchone()
                return Token.from_row(row) if row is not None else None

