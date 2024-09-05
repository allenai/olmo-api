import datetime
from typing import Optional

from flask import Request, current_app, request
from werkzeug import exceptions
from zoneinfo import ZoneInfo

from src.auth.auth0 import require_auth

from .token import Token


def token_from_request(r: Request) -> Optional[str]:
    auth = r.headers.get("Authorization")
    if auth is None:
        return None
    try:
        scheme, token = auth.split(" ", maxsplit=1)
        if scheme.lower() != "bearer":
            return None
        return token
    except ValueError:
        return None


def request_agent() -> Optional[Token]:
    with require_auth.acquire("profile") as token:
        if token is None:
            return None

        return Token(
            client=token.sub,
            created=datetime.datetime.fromtimestamp(token.iat, tz=ZoneInfo("UTC")),
            expires=datetime.datetime.fromtimestamp(token.exp, tz=ZoneInfo("UTC")),
            creator=token.iss,
        )


def authn() -> Token:
    agent = request_agent()
    if agent is None or agent.expired():
        raise exceptions.Unauthorized()

    current_app.logger.info(
        {
            "path": request.path,
            "message": f"authorized client {agent.client}",
            "client": agent.client,
            "created": agent.created,
            "expires": agent.expires,
        }
    )

    return agent
