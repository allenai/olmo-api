from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus

import requests
from flask import Request, current_app, request
from opentelemetry import trace
from opentelemetry.trace.span import INVALID_SPAN
from werkzeug import exceptions

from core.auth import Token, UserInfo
from src.auth.resource_protectors import anonymous_auth_protector
from src.config.get_config import get_config


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

    current_span = trace.get_current_span()
    if current_span is not INVALID_SPAN:
        current_span.set_attribute("client.id", agent.client)
        current_span.set_attribute("client.created", str(agent.created))
        current_span.set_attribute("client.expires", str(agent.expires))

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
    response = requests.get(f"https://{get_config().auth.domain}/userinfo", headers=headers)

    if response.status_code == HTTPStatus.OK:
        user_info = response.json()
        email = user_info.get("email")
        first_name = user_info.get("given_name")
        last_name = user_info.get("family_name")

        return UserInfo(email=email, first_name=first_name, last_name=last_name)
    current_app.logger.error("Error fetching user info: %s %s", response.status_code, response.text)
    return None
