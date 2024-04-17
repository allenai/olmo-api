from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg_pool import ConnectionPool

from src import obj

UserRow = tuple[str, str, datetime, Optional[datetime], str]


@dataclass
class User:
    id: obj.ID
    client: str
    terms_accepted_date: datetime
    acceptance_revoked_date: Optional[datetime]
    terms_version_accepted: str

    @classmethod
    def from_row(cls, row: UserRow) -> "User":
        [
            id,
            client,
            terms_accepted_date,
            acceptance_revoked_date,
            terms_version_accepted,
        ] = row

        return cls(
            id=id,
            client=client,
            terms_accepted_date=terms_accepted_date,
            acceptance_revoked_date=acceptance_revoked_date,
            terms_version_accepted=terms_version_accepted,
        )


class Store:
    pool: ConnectionPool

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def get_by_client(self, client: str) -> Optional[User]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    SELECT
                        id, client, terms_accepted_date, acceptance_revoked_date, terms_version_accepted
                    FROM
                        user
                    WHERE
                        client = %s
                """

                row = cur.execute(query=q, params=(client)).fetchone()
                return User.from_row(row=row) if row is not None else None

    def create(
        self,
        client: str,
        terms_accepted_date: Optional[datetime] = None,
        acceptance_revoked_date: Optional[datetime] = None,
        terms_version_accepted: Optional[str] = None,
    ) -> User:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    INSERT INTO
                        user (id, client, terms_accepted_date, acceptance_revoked_date, terms_version_accepted)
                    VALUES
                        (%s, %s, %s, %s, %s, %s)
                    RETURNING
                    id, client, terms_accepted_date, acceptance_revoked_date, terms_version_accepted
                """

                new_id = obj.NewID("user")
                row = cur.execute(
                    query=q,
                    params=(
                        new_id,
                        client,
                        terms_accepted_date,
                        acceptance_revoked_date,
                        terms_version_accepted,
                    ),
                ).fetchone()

                if row is None:
                    raise RuntimeError("failed to create user")

                return User.from_row(row)
