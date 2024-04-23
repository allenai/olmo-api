from typing import Self

from psycopg_pool import ConnectionPool

from . import config
from .dao import completion, datachip, label, message, template, token, user


class Client:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.token = token.Store(pool)
        self.template = template.Store(pool)
        self.message = message.Store(pool)
        self.label = label.Store(pool)
        self.completion = completion.Store(pool)
        self.datachip = datachip.Store(pool)
        self.user = user.Store(pool=pool)

    def close(self):
        self.pool.close()

    @classmethod
    def from_config(cls, c: config.Database) -> Self:
        return cls(
            pool=ConnectionPool(
                conninfo=c.conninfo, min_size=c.min_size, max_size=c.max_size
            )
        )
