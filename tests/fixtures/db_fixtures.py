import logging
from pathlib import Path

import pytest
from psycopg import Connection
from pytest_postgresql import factories
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

postgresql = factories.postgresql(
    "postgresql_proc",
)


@pytest.fixture
def dbc(postgresql: Connection):
    cfg = get_config.Config.load("./test.config.json")

    cur = postgresql.cursor()
    result = cur.execute("""
    select * from message limit 10;
                         """)
    LOGGER.error(result.fetchall())
    postgresql.commit()
    cur.close()

    cfg.db.conninfo = (
        f"postgresql://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    )

    return db.Client.from_config(cfg.db)


@pytest.fixture
def sql_alchemy(
    postgresql: Connection,
):
    cfg = get_config.Config.load("./test.config.json")

    cfg.db.conninfo = (
        f"postgresql://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    )

    dbc = db.Client.from_config(cfg.db)

    db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)
    with session_maker() as session:
        yield session
