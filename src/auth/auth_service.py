from dataclasses import dataclass
from datetime import UTC, datetime

import requests
from flask import Request, current_app, request
from werkzeug import exceptions

from src.auth.resource_protectors import anonymous_auth_protector
from src.config.get_config import cfg

from .token import Token


@dataclass
class UserInfo:
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


def token_from_request(r: Request) -> str | None:
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


def request_agent() -> Token | None:
    token = anonymous_auth_protector.get_token()
    if token is not None:
        # This will happen if we get an anonymous user, this is supposed to be the anonymous user id we get from the req
        if isinstance(token, str):
            return Token(client=token, is_anonymous_user=True, token=token)
        # User is logged in through Auth0
        return Token(
            client=token.sub,
            is_anonymous_user=False,
            created=datetime.fromtimestamp(token.iat, tz=UTC),
            expires=datetime.fromtimestamp(token.exp, tz=UTC),
            creator=token.iss,
            token=token,
        )
    return None


def authn() -> Token:
    agent = request_agent()
    if agent is None or agent.expired():
        raise exceptions.Unauthorized

    current_app.logger.info({
        "path": request.path,
        "message": f"authorized client {agent.client}",
        "client": agent.client,
        "created": agent.created,
        "expires": agent.expires,
    })

    return agent


def get_user_info() -> UserInfo | None:
    auth = request.headers.get("Authorization")
    headers = {"Authorization": f"{auth}", "Content-Type": "application/json"}
    response = requests.get(f"https://{cfg.auth.domain}/userinfo", headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        email = user_info.get("email")
        first_name = user_info.get("given_name")
        last_name = user_info.get("family_name")

        return UserInfo(email=email, first_name=first_name, last_name=last_name)
    current_app.logger.error("Error fetching user info:", response.status_code, response.text)
    return None
