from pathlib import Path

import pytest
from psycopg import Connection
from pytest_postgresql import factories
from sqlalchemy.orm import sessionmaker

from src.config import get_config
from src.config.Config import Config
from src.db import Client
from src.db.init_sqlalchemy import make_db_engine

postgresql_proc = factories.postgresql_proc(
    load=[
        Path("./schema/01-local.sql"),
        Path("./schema/02-schema.sql"),
        Path("./schema/03-add_models.sql"),
    ],
)

postgresql = factories.postgresql(
    "postgresql_proc",
)


@pytest.fixture
def cfg(postgresql: Connection):
    cfg = get_config.Config.load("./test.config.json")

    # dynamically set connection based on pytest_postgresql
    cfg.db.conninfo = (
        f"postgresql://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    )
    return cfg


@pytest.fixture
def dbc(cfg: Config):
    dbc = Client.from_config(cfg.db)
    yield dbc
    dbc.close()


@pytest.fixture
def sql_alchemy(dbc: Client, cfg: Config):
    db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)

    with session_maker() as session:
        yield session
    db_engine.dispose()
