
from src.config import cfg
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests


from flask import Request, current_app, request
from werkzeug import exceptions

from src.auth.auth0 import require_auth

from .token import Token
@dataclass
class UserInfo:
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

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
    with require_auth.acquire() as token:
        if token is None:
            return None

        return Token(
            client=token.sub,
            created=datetime.fromtimestamp(token.iat, tz=timezone.utc),
            expires=datetime.fromtimestamp(token.exp, tz=timezone.utc),
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

def get_user_info() -> Optional[UserInfo]:
    auth = request.headers.get("Authorization")
    headers = {
            "Authorization": f"{auth}",
            "Content-Type": "application/json"
        }
    response = requests.get(f'https://{cfg.auth.domain}/userinfo', headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        email = user_info.get('email')
        first_name = user_info.get('given_name')
        last_name = user_info.get('family_name')

        return UserInfo(email=email, first_name=first_name, last_name=last_name)
    else:
        current_app.logger.error('Error fetching user info:', response.status_code, response.text)
        return None  
