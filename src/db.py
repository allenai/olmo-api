import logging
import os
from typing import Self

from psycopg_pool import ConnectionPool

from . import config
from .dao import completion, datachip, label, message, template, user


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
    def from_config(cls, c: config.Database) -> Self:
        logging.getLogger(("psycopg.pool")).setLevel(logging.INFO)
        logging.getLogger().debug(
            f"Creating connection pool for worker pid {os.getpid()} with min_size {c.min_size}, max_size {c.max_size}"
        )
        return cls(
            pool=ConnectionPool(
                conninfo=c.conninfo,
                min_size=c.min_size,
                max_size=c.max_size,
                check=ConnectionPool.check_connection,
            )
        )
