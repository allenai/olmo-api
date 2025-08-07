import logging
from pathlib import Path

from psycopg import Connection
from pytest_postgresql import factories

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


def test_example_postgres(postgresql: Connection):
    """Check main postgresql fixture."""
    cur = postgresql.cursor()
    result = cur.execute("""
    select * from message limit 10;
                         """)
    LOGGER.error(result.fetchall())
    postgresql.commit()
    cur.close()
