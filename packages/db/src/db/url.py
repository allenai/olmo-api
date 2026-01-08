from sqlalchemy import URL
from sqlalchemy import make_url as sqla_make_url


def make_url(conninfo: str | URL) -> URL:
    return sqla_make_url(conninfo).set(drivername="postgresql+psycopg")
