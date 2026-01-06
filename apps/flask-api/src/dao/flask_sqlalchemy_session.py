"""
Flask-SQLAlchemy-Session
-----------------------

Provides an SQLAlchemy scoped session that creates
unique sessions per Flask request

Taken from https://github.com/e-c-d/flask-sqlalchemy-session2024
"""

from typing import cast

from flask import current_app, g
from sqlalchemy.orm import Session, scoped_session
from werkzeug.local import LocalProxy

__all__ = ["current_session", "flask_scoped_session"]


def _get_session() -> Session:
    return flask_scoped_session.get_scoped_session_from_flask()


current_session = cast(Session, LocalProxy(_get_session))
"""Provides the current SQL Alchemy session within a request.

Will raise an exception if no :data:`~flask.current_app` is available or it has
not been initialized with a :class:`flask_scoped_session`
"""


class flask_scoped_session(scoped_session):  # noqa: N801
    """A :class:`~sqlalchemy.orm.scoping.scoped_session` whose scope is set to
    the Flask application context.
    """

    flask_app_context_attribute = "_sqlalchemy_scoped_session"

    def __init__(self, session_factory, app=None):
        """
        :param session_factory: A callable that returns a :class:`~sqlalchemy.orm.session.Session`
        :param app: A :class:`~flask.Flask` application to be automatically registered with init_app
        """
        super().__init__(session_factory, self.__scopefunc)
        self.__apps = set()
        if app is not None:
            self.init_app(app)

    def __scopefunc(self):
        # Check that the app has been registered. See "init_app()" for why.
        assert current_app._get_current_object() in self.__apps, (  # noqa: SLF001 # type: ignore
            "you must register the app with flask_scoped_session.init_app(app) before using it"
        )

        return g._get_current_object()  # noqa: SLF001

    def init_app(self, app):
        """
        Install an appcontext teardown handler which closes the current scoped session. The
        SQLAlchemy documentation warns that failing to call scoped_session.remove() can
        result in resource leaks.

        https://docs.sqlalchemy.org/en/20/orm/contextual.html#using-custom-created-scopes

        :param app: a :class:`~flask.Flask` application
        """
        attr = self.flask_app_context_attribute

        @app.teardown_appcontext
        def remove_scoped_session(*args, **kwargs):
            self.remove()

        # Permanently associate the app with this flask_scoped_session.
        setattr(app, attr, self)
        self.__apps.add(app)

    @classmethod
    def get_scoped_session_from_flask(cls):
        return getattr(current_app, cls.flask_app_context_attribute)
