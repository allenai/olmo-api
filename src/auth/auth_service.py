from typing import Optional

from flask import Request, Response, current_app, request
from werkzeug import exceptions
from werkzeug.wrappers import response

from src import db
from src.dao import token


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


def request_agent(dbc: db.Client) -> Optional[token.Token]:
    provided = request.cookies.get("token", default=token_from_request(request))
    if provided is None:
        return None
    return dbc.token.get(provided, token.TokenType.Auth)


def authn(dbc: db.Client) -> token.Token:
    agent = request_agent(dbc)
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


def set_auth_cookie(
    resp: Response | response.Response, token: token.Token
) -> Response | response.Response:
    resp.set_cookie(
        key="token",
        value=token.token,
        expires=token.expires,
        httponly=True,
        secure=True,
        samesite="Strict",
    )
    return resp
