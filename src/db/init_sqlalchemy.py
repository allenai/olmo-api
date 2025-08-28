from psycopg_pool import ConnectionPool
from sqlalchemy import URL, Engine, create_engine, make_url

from src.config.Config import Database, SQLAlchemyConfig


def make_psycopg3_url(conninfo) -> URL:
    return make_url(conninfo).set(drivername="postgresql+psycopg")


def make_db_engine(config: Database, pool: ConnectionPool, sql_alchemy: SQLAlchemyConfig) -> Engine:
    url = make_psycopg3_url(config.conninfo)

    return create_engine(url, creator=pool.getconn, pool_size=sql_alchemy.pool_size)
