import structlog
import os
from functools import lru_cache

from psycopg_pool import ConnectionPool

logger = structlog.get_logger(__name__)


@lru_cache
def create_connection_pool(conninfo: str, min_size: int, max_size: int) -> ConnectionPool:
    logger.debug(
        "creating_connection_pool",
        worker_pid=os.getpid(),
        min_size=min_size,
        max_size=max_size,
    )

    return ConnectionPool(
        conninfo=conninfo,
        min_size=min_size,
        max_size=max_size,
        check=ConnectionPool.check_connection,
        kwargs={"application_name": f"olmo-api:{os.getenv('SHA') or ''}"},
    )
