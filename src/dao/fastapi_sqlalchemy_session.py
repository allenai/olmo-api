"""
FastAPI-SQLAlchemy-Session
---------------------------

Provides an SQLAlchemy session dependency for FastAPI that creates
unique sessions per request and properly manages their lifecycle.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session


def get_session_factory(request: Request):
    """
    Get the session factory from FastAPI app state.

    The session factory is initialized during app startup in the lifespan context manager.
    """
    return request.app.state.session_maker


def get_db_session(
    session_factory=Depends(get_session_factory),
) -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a SQLAlchemy session.

    This replaces Flask's flask_scoped_session and g-based scoping.
    The session is automatically created at the start of the request,
    committed if successful, rolled back on error, and always closed
    at the end of the request.

    Usage:
        @router.get("/items")
        async def get_items(session: DBSession):
            # Use session here
            items = session.query(Item).all()
            return items
    """
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Type alias for dependency injection
# This makes it easy to inject the session in route handlers
DBSession = Annotated[Session, Depends(get_db_session)]
