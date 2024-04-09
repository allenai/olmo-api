from src.dao import token
from src import auth, db
from typing import Optional
from flask import request, current_app, Request
from werkzeug import exceptions


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
        provided = request.cookies.get(
            "token",
            default=token_from_request(request)
        )
        if provided is None:
            return None
        return dbc.token.get(provided, token.TokenType.Auth)

def authn(dbc: db.Client) -> token.Token:
    agent = request_agent(dbc)
    if agent is None or agent.expired():
        raise exceptions.Unauthorized()

    current_app.logger.info({
        "path": request.path,
        "message": f"authorized client {agent.client}",
        "client": agent.client,
        "created": agent.created,
        "expires": agent.expires,
    })

    return agent