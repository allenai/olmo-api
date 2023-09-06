from psycopg_pool import ConnectionPool
from .dao import token, template, message, label, completion

import os
import json

class Client:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.token = token.Store(pool)
        self.template = template.Store(pool)
        self.message = message.Store(pool)
        self.label = label.Store(pool)
        self.completion = completion.Store(pool)

    def close(self):
        self.pool.close()

    @staticmethod
    def from_env() -> 'Client':
        p = os.getenv("LLMX_DB_CONFIG", "/secret/db/config.json")
        with open(p) as f:
            config = json.load(f)
            return Client(ConnectionPool(**config))

