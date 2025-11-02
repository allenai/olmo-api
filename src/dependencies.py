"""
Application Dependencies
-------------------------

FastAPI dependency injection providers for shared resources.
Replaces app.state pattern with proper dependency injection.
"""
from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.config.get_config import Config, get_config
from src.message.GoogleCloudStorage import GoogleCloudStorage


# Config dependency (cached singleton)
@lru_cache
def get_app_config() -> Config:
    """Get application configuration (cached singleton)"""
    return get_config()


# Database client dependency
def get_db_client(config: Annotated[Config, Depends(get_app_config)]) -> db.Client:
    """Get database client from config"""
    # Return cached client if available, otherwise create new one
    if not hasattr(get_db_client, "_client_cache"):
        get_db_client._client_cache = db.Client.from_config(config.db)
    return get_db_client._client_cache


# Storage client dependency
def get_storage_client(
    config: Annotated[Config, Depends(get_app_config)]
) -> GoogleCloudStorage:
    """Get Google Cloud Storage client"""
    if not hasattr(get_storage_client, "_storage_cache"):
        get_storage_client._storage_cache = GoogleCloudStorage(
            bucket_name=config.google_cloud_services.storage_bucket
        )
    return get_storage_client._storage_cache


# Session factory dependency
@lru_cache
def create_session_factory(config: Config) -> sessionmaker:
    """Create and cache SQLAlchemy session factory"""
    from src.db.init_sqlalchemy import make_db_engine

    dbc = db.Client.from_config(config.db)
    db_engine = make_db_engine(
        config.db,
        pool=dbc.pool,
        sql_alchemy=config.sql_alchemy
    )
    return sessionmaker(db_engine, expire_on_commit=False, autoflush=True)


def get_session_factory(config: Annotated[Config, Depends(get_app_config)]) -> sessionmaker:
    """Get SQLAlchemy session factory"""
    return create_session_factory(config)


# Database session dependency
def get_db_session(
    session_factory: Annotated[sessionmaker, Depends(get_session_factory)]
) -> Generator[Session, None, None]:
    """Provide database session with automatic lifecycle management"""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Type aliases for clean dependency injection
AppConfig = Annotated[Config, Depends(get_app_config)]
DBClient = Annotated[db.Client, Depends(get_db_client)]
StorageClient = Annotated[GoogleCloudStorage, Depends(get_storage_client)]
SessionFactory = Annotated[sessionmaker, Depends(get_session_factory)]
DBSession = Annotated[Session, Depends(get_db_session)]