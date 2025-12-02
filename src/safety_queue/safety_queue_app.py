from functools import lru_cache

import procrastinate
from psycopg_pool import ConnectionPool


@lru_cache
def create_safety_queue_app(connection_pool: ConnectionPool) -> procrastinate.App:
    return procrastinate.App(connector=procrastinate.SyncPsycopgConnector())
