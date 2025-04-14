from typing import Self

from psycopg_pool import ConnectionPool

from src.config.Config import Database
from src.dao import completion, datachip, label, message, template, user
from src.db.connection_pool import create_connection_pool


class Client:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.template = template.Store(pool)
        self.message = message.Store(pool)
        self.label = label.Store(pool)
        self.completion = completion.Store(pool)
        self.datachip = datachip.Store(pool)
        self.user = user.Store(pool=pool)

    def close(self):
        self.pool.close()

    @classmethod
    def from_config(cls, config: Database) -> Self:
        return cls(pool=create_connection_pool(config.conninfo, config.min_size, config.max_size))
