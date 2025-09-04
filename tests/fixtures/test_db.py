import logging
from pathlib import Path

import pytest
from flask import Flask
from psycopg import Connection
from pytest_postgresql import factories
from sqlalchemy.orm import sessionmaker

from src import db
from src.config import get_config
from src.dao.flask_sqlalchemy_session import flask_scoped_session
from src.dao.label import Rating
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
def app():
    return Flask(__name__)


@pytest.fixture
def test_dbc(postgresql: Connection, app: Flask):
    cfg = get_config.Config.load("./test.config.json")

    cfg.db.conninfo = (
        f"postgresql://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    )

    dbc = db.Client.from_config(cfg.db)

    db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)
    flask_scoped_session(session_maker, app=app)

    return dbc


def test_example_postgres(test_dbc: db.Client):
    """Check main postgresql fixture."""
    label = test_dbc.label.create(message="hello", rating=Rating.POSITIVE, creator="", comment=None)

    found = test_dbc.label.get(label.id)

    assert found is not None
