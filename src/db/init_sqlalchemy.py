from sqlalchemy import Engine, create_engine, make_url

from src.config.Config import Database


def make_db_engine(config: Database) -> Engine:
    url = make_url(config.conninfo)
    url_with_correct_driver = url.set(drivername="postgresql+psycopg")

    return create_engine(
        url_with_correct_driver,
    )
