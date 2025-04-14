import logging
import os
from functools import lru_cache

from psycopg_pool import ConnectionPool
from sqlalchemy import URL, create_pool_from_url, make_url


def make_psycopg3_url(conninfo) -> URL:
    return make_url(conninfo).set(drivername="postgresql+psycopg")


@lru_cache
def create_connection_pool(conninfo: str, min_size: int, max_size: int):
    logging.getLogger().debug(
        "Creating connection pool for worker pid %s with min_size %s, max_size %s",
        os.getpid(),
        min_size,
        max_size,
    )

    url = make_psycopg3_url(conninfo)

    return create_pool_from_url(url)

    return ConnectionPool(
        conninfo=conninfo,
        min_size=min_size,
        max_size=max_size,
        check=ConnectionPool.check_connection,
        kwargs={"application_name": f"olmo-api:{os.getenv('SHA') or ''}"},
    )
