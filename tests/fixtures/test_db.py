import logging
from pathlib import Path

import pytest
from psycopg import Connection
from pytest_postgresql import factories

from src.config.Config import Config

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


@pytest.fixture(scope="function")
def app():
    app = create_app()
    yield app


def test_example_postgres(postgresql: Connection):
    """Check main postgresql fixture."""

    connection = f"postgresql+psycopg2://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"

    dbc = db.Client.from_config(cfg.db)
    # db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    # session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)
    # flask_scoped_session(session_maker, app=app)

    cur = postgresql.cursor()
    result = cur.execute("""
    select * from message limit 10;
                         """)
    LOGGER.error(result.fetchall())
    postgresql.commit()
    cur.close()
