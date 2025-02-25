from datetime import datetime

from psycopg_pool import ConnectionPool

from src import obj
from src.api_interface import APIInterface

UserRow = tuple[str, str, datetime, datetime | None]


class User(APIInterface):
    id: obj.ID
    client: str
    terms_accepted_date: datetime
    acceptance_revoked_date: datetime | None

    @classmethod
    def from_row(cls, row: UserRow) -> "User":
        [
            id,
            client,
            terms_accepted_date,
            acceptance_revoked_date,
        ] = row

        return cls(
            id=id,
            client=client,
            terms_accepted_date=terms_accepted_date,
            acceptance_revoked_date=acceptance_revoked_date,
        )


class Store:
    pool: ConnectionPool

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    @staticmethod
    def create_new_id() -> str:
        return obj.NewID("user")

    def get_by_client(self, client: str) -> User | None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    SELECT
                        id, client, terms_accepted_date, acceptance_revoked_date
                    FROM
                        olmo_user
                    WHERE
                        client = %(client)s
                """

                row = cur.execute(query=q, params={"client": client}).fetchone()
                return User.from_row(row=row) if row is not None else None

    def update(
        self,
        client: str,
        id: str | None = None,
        terms_accepted_date: datetime | None = None,
        acceptance_revoked_date: datetime | None = None,
    ) -> User | None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    UPDATE
                        olmo_user
                    SET
                        client = COALESCE(%(client)s, client),
                        terms_accepted_date = COALESCE(%(terms_accepted_date)s, terms_accepted_date),
                        acceptance_revoked_date = COALESCE(%(acceptance_revoked_date)s, acceptance_revoked_date)
                    WHERE id = %(id)s OR client = %(client)s
                    RETURNING
                        id, client, terms_accepted_date, acceptance_revoked_date
                """

                row = cur.execute(
                    q,
                    {
                        "id": id,
                        "client": client,
                        "terms_accepted_date": terms_accepted_date,
                        "acceptance_revoked_date": acceptance_revoked_date,
                    },
                ).fetchone()

                return User.from_row(row) if row is not None else None

    def create(
        self,
        client: str,
        terms_accepted_date: datetime | None = None,
        acceptance_revoked_date: datetime | None = None,
    ) -> User:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                q = """
                    INSERT INTO
                        olmo_user (id, client, terms_accepted_date, acceptance_revoked_date)
                    VALUES
                        (%(id)s, %(client)s, %(terms_accepted_date)s, %(acceptance_revoked_date)s)
                    RETURNING
                        id, client, terms_accepted_date, acceptance_revoked_date
                """

                new_id = obj.NewID("user")
                row = cur.execute(
                    query=q,
                    params={
                        "id": new_id,
                        "client": client,
                        "terms_accepted_date": terms_accepted_date,
                        "acceptance_revoked_date": acceptance_revoked_date,
                    },
                ).fetchone()

                if row is None:
                    raise RuntimeError("failed to create user")

                return User.from_row(row)
