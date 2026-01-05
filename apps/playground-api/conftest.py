import os
from pathlib import Path

import pytest
from flask import Flask
from psycopg import Connection
from psycopg_pool import ConnectionPool
from pytest_postgresql import factories
from sqlalchemy.orm import sessionmaker

from src.config.Config import Config
from src.db.init_psycopg import Client
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
def cfg(postgresql: Connection) -> Config:
    cfg = Config.load("./test.config.json")

    # dynamically set connection based on pytest_postgresql
    cfg.db.conninfo = f"postgresql://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    return cfg


@pytest.fixture(params=[pytest.param("", marks=pytest.mark.integration)])
def dbc(cfg: Config, postgresql: Connection):
    pool: ConnectionPool = ConnectionPool(
        conninfo=f"postgresql://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}",
        min_size=cfg.db.min_size,
        max_size=cfg.db.max_size,
        check=ConnectionPool.check_connection,
        open=True,
        kwargs={"application_name": f"olmo-api:{os.getenv('SHA') or ''}"},
    )

    dbc = Client(pool=pool)
    yield dbc
    dbc.close()


@pytest.fixture(params=[pytest.param("", marks=pytest.mark.integration)])
def sql_alchemy(dbc: Client, cfg: Config):
    db_engine = make_db_engine(cfg.db, pool=dbc.pool)
    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)

    with session_maker() as session:
        yield session
    db_engine.dispose()


@pytest.fixture
def flask_request_context():
    app = Flask(__name__)
    with app.test_request_context("/"):
        yield
