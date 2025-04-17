from sqlalchemy import URL, Engine, create_engine, make_url

from src.config.Config import Database


def make_psycopg3_url(conninfo) -> URL:
    return make_url(conninfo).set(drivername="postgresql+psycopg")


def make_db_engine(config: Database) -> Engine:
    url = make_psycopg3_url(config.conninfo)

    return create_engine(url, pool_size=1, max_overflow=config.max_size)
