import logging
from pathlib import Path

import pytest
from psycopg import Connection
from pytest_postgresql import factories
from sqlalchemy.orm import sessionmaker, Session as SessionMaker

from src import db
from src.config import get_config
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
def dbc(postgresql: Connection):
    cfg = get_config.Config.load("./test.config.json")

    cfg.db.conninfo = (
        f"postgresql://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    )

    return db.Client.from_config(cfg.db)


@pytest.fixture
def sql_alchemy_session_maker(dbc: db.Client, postgresql: Connection):
    cfg = get_config.Config.load("./test.config.json")

    cfg.db.conninfo = (
        f"postgresql://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    )

    db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)
    return session_maker


@pytest.fixture(scope="function")
def sql_alchemy(sql_alchemy_session_maker: sessionmaker[SessionMaker]):
    with sql_alchemy_session_maker() as session:
        yield session
