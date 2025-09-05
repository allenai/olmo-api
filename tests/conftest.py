import logging
from pathlib import Path

import pytest
from psycopg import Connection
from pytest_postgresql import factories
from sqlalchemy.orm import sessionmaker, Session as SessionMaker

from src import db
from src.config import get_config
from src.db.init_sqlalchemy import make_db_engine
from pytest_postgresql.executor import PostgreSQLExecutor
from pytest_postgresql.janitor import DatabaseJanitor

LOGGER = logging.getLogger(__name__)

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


@pytest.fixture(scope="session")
def database_setup(postgresql_proc: PostgreSQLExecutor):
    logging.getLogger().error("Setting up DB")
    with DatabaseJanitor(
        user=postgresql_proc.user,
        host=postgresql_proc.host,
        port=postgresql_proc.port,
        dbname=postgresql_proc.dbname,
        version=postgresql_proc.version,
        template_dbname=postgresql_proc.template_dbname,
    ):
        yield


@pytest.fixture(scope="session")
def sql_alchemy_session_maker(database_setup, postgresql_proc: PostgreSQLExecutor):
    logging.getLogger().error("Starting up SQL Alchemy session maker")
    cfg = get_config.Config.load("./test.config.json")

    cfg.db.conninfo = (
        f"postgresql://{postgresql_proc.user}:@{postgresql_proc.host}:{postgresql_proc.port}/{postgresql_proc.dbname}"
    )
    dbc = db.Client.from_config(cfg.db)

    db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)

    yield session_maker
    db_engine.dispose()


@pytest.fixture
def dbc(database_setup, postgresql_proc: PostgreSQLExecutor):
    cfg = get_config.Config.load("./test.config.json")

    cfg.db.conninfo = (
        f"postgresql://{postgresql_proc.user}:@{postgresql_proc.host}:{postgresql_proc.port}/{postgresql_proc.dbname}"
    )

    dbc = db.Client.from_config(cfg.db)
    yield dbc
    dbc.close()


@pytest.fixture
def sql_alchemy(sql_alchemy_session_maker: sessionmaker[SessionMaker]):
    logging.getLogger().error("Starting up SQL Alchemy session")
    with sql_alchemy_session_maker() as session:
        yield session
