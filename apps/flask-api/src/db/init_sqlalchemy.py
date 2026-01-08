from db.url import make_url
from psycopg_pool import ConnectionPool
from sqlalchemy import Engine, NullPool, create_engine

from src.config.Config import Database


def make_db_engine(config: Database, pool: ConnectionPool) -> Engine:
    url = make_url(config.conninfo)

    return create_engine(url, creator=pool.getconn, poolclass=NullPool)
