import logging
from pathlib import Path

import pytest
from psycopg import Connection
from pytest_postgresql import factories
from sqlalchemy.orm import Session as SessionMaker
from sqlalchemy.orm import sessionmaker

from src import db
from src.config import get_config
from src.db.init_sqlalchemy import make_db_engine

LOGGER = logging.getLogger(__name__)

postgresql_proc = factories.postgresql_proc(
    load=[
        Path("./schema/01-local.sql"),
        Path("./schema/02-schema.sql"),
        Path("./schema/03-add_models.sql"),
    ],
)

postgressql = factories.postgresql(
    "postgresql_proc",
)


@pytest.fixture
def sql_alchemy_session_maker(postgressql: Connection):
    logging.getLogger().error("Starting up SQL Alchemy session maker")
    cfg = get_config.Config.load("./test.config.json")

    cfg.db.conninfo = f"postgresql://{postgressql.info.user}:@{postgressql.info.host}:{postgressql.info.port}/{postgressql.info.dbname}"
    dbc = db.Client.from_config(cfg.db)

    db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)

    yield session_maker
    db_engine.dispose()

    dbc.close()


@pytest.fixture
def dbc(postgressql: Connection):
    cfg = get_config.Config.load("./test.config.json")

    cfg.db.conninfo = f"postgresql://{postgressql.info.user}:@{postgressql.info.host}:{postgressql.info.port}/{postgressql.info.dbname}"

    dbc = db.Client.from_config(cfg.db)
    yield dbc
    dbc.close()


@pytest.fixture
def sql_alchemy(sql_alchemy_session_maker: sessionmaker[SessionMaker]):
    logging.getLogger().error("Starting up SQL Alchemy session")
    with sql_alchemy_session_maker() as session:
        yield session
