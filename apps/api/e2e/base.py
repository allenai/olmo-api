import uuid
from dataclasses import dataclass
from typing import Any
from unittest import TestCase

import pytest
import requests
from fastapi.testclient import TestClient

from main import app

from .conftest import settings

ANONYMOUS_USER_ID_HEADER = "X-Anonymous-User-ID"


@dataclass(kw_only=True)
class AuthenticatedClient:
    client: str
    token: str | None
    is_anonymous: bool = False


class IntegrationTest(TestCase):
    client: TestClient
    auth0_token: str | None = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    @classmethod
    def auth(cls, u: AuthenticatedClient) -> dict[str, str]:
        if u.is_anonymous:
            return {ANONYMOUS_USER_ID_HEADER: str(u.client)}
        return {"Authorization": f"Bearer {u.token}"}

    @classmethod
    def json(cls, h: dict[str, str]) -> dict[str, str]:
        return {"Content-Type": "application/json", **h}

    def get_auth0_token(self):
        if self.auth0_token is None:
            payload = {
                "client_id": settings.E2E_AUTH0_CLIENT_ID,
                "client_secret": settings.E2E_AUTH0_CLIENT_SECRET,
                "audience": settings.AUTH_AUDIENCE,
                "grant_type": "client_credentials",
            }
            headers = {"content-type": "application/json"}

            response = requests.post(
                f"https://{settings.AUTH_DOMAIN}/oauth/token", json=payload, headers=headers, timeout=5
            )
            response.raise_for_status()

            self.auth0_token = response.json().get("access_token")

        return self.auth0_token

    def user(self, *, anonymous: bool = False) -> AuthenticatedClient:
        auth0_token = None

        if anonymous:
            headers = {ANONYMOUS_USER_ID_HEADER: str(uuid.uuid4())}
        else:
            auth0_token = self.get_auth0_token()
            headers = {"Authorization": f"Bearer {self.get_auth0_token()}"}

        r = self.client.get("/v5/whoami", headers=headers)
        r.raise_for_status()
        client_id = r.json()["client"]
        return AuthenticatedClient(client=client_id, token=auth0_token, is_anonymous=anonymous)

    def auth_user(self):
        return self.auth(self.user())
