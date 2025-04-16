import logging
import os
from functools import lru_cache

from psycopg_pool import ConnectionPool


@lru_cache
def create_connection_pool(conninfo: str, min_size: int, max_size: int) -> ConnectionPool:
    logging.getLogger().debug(
        "Creating connection pool for worker pid %s with min_size %s, max_size %s",
        os.getpid(),
        min_size,
        max_size,
    )

    return ConnectionPool(
        conninfo=conninfo,
        min_size=min_size,
        max_size=max_size,
        check=ConnectionPool.check_connection,
        kwargs={"application_name": f"olmo-api:{os.getenv('SHA') or ''}"},
    )
