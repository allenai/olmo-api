import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from psycopg import Connection
from psycopg_pool import ConnectionPool
from pytest_postgresql import factories
from sqlalchemy.orm import Session, sessionmaker

from app import create_app
from src.config import get_config
from src.config.Config import Config
from src.db import Client
from src.db.init_sqlalchemy import make_db_engine
from src.dependencies import (
    get_app_config,
    get_db_client,
    get_db_session,
    get_storage_client,
)

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
    db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)

    with session_maker() as session:
        yield session
    db_engine.dispose()


# FastAPI Test Fixtures with Dependency Overrides


@pytest.fixture
def test_storage_client():
    """Mock storage client for tests"""
    return Mock()


@pytest.fixture(params=[pytest.param("", marks=pytest.mark.integration)])
def test_client(sql_alchemy: Session, dbc: Client, cfg: Config, test_storage_client):
    """
    FastAPI TestClient with all dependencies overridden for integration tests.

    This fixture provides a configured TestClient that overrides all dependency
    injection functions to use test fixtures instead of real services.
    """
    app = create_app()

    # Override all dependencies with test fixtures
    app.dependency_overrides[get_db_session] = lambda: sql_alchemy
    app.dependency_overrides[get_db_client] = lambda: dbc
    app.dependency_overrides[get_storage_client] = lambda: test_storage_client
    app.dependency_overrides[get_app_config] = lambda: cfg

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()
