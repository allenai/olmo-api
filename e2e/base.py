import os
import uuid
from dataclasses import dataclass
from unittest import TestCase

import requests

from src.constants import ANONYMOUS_USER_ID_HEADER


@dataclass
class AuthenticatedClient:
    client: str
    token: str | None
    is_anonymous: bool = False


class IntegrationTest(TestCase):
    origin = os.environ.get("ORIGIN", "http://localhost:8000")
    auth0_token: str | None = None

    def get_auth0_token(self):
        if self.auth0_token is None:
            payload = {
                "client_id": "HUw7VgztNNVEvt54pZoLwlqWt26vzlYb",
                "client_secret": os.getenv("E2E_AUTH0_CLIENT_SECRET"),
                "audience": "https://olmo-api.allen.ai",
                "grant_type": "client_credentials",
            }
            headers = {"content-type": "application/json"}
            response = requests.post(
                "https://allenai-public.us.auth0.com/oauth/token",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            self.auth0_token = response.json().get("access_token")

        return self.auth0_token

    def user(self, email: str = "", anonymous: bool = False) -> AuthenticatedClient:
        auth0_token = None

        if anonymous:
            headers = {ANONYMOUS_USER_ID_HEADER: str(uuid.uuid4())}
        else:
            auth0_token = self.get_auth0_token()
            headers = {"Authorization": f"Bearer {self.get_auth0_token()}"}

        r = requests.get(
            f"{self.origin}/v3/whoami",
            headers=headers,
        )
        r.raise_for_status()
        client = r.json()["client"]
        return AuthenticatedClient(client, auth0_token, is_anonymous=anonymous)

    def auth(self, u: AuthenticatedClient) -> dict[str, str]:
        if u.is_anonymous:
            return {ANONYMOUS_USER_ID_HEADER: str(u.client)}
        return {"Authorization": f"Bearer {u.token}"}

    def json(self, h: dict[str, str]) -> dict[str, str]:
        return {"Content-Type": "application/json", **h}
