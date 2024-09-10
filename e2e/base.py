import os
from dataclasses import dataclass
from unittest import TestCase

import requests


@dataclass
class AuthenticatedClient:
    client: str
    token: str


class IntegrationTest(TestCase):
    origin = os.environ.get("ORIGIN", "http://localhost:8000")
    auth0_token: str

    @classmethod
    def setUpClass(cls):
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

        cls.auth0_token = response.json().get("access_token")

    def user(self, email: str) -> AuthenticatedClient:
        r = requests.get(
            f"{self.origin}/v3/whoami",
            headers={"Authorization": f"Bearer {self.auth0_token}"},
        )
        r.raise_for_status()
        client = r.json()["client"]
        return AuthenticatedClient(client, self.auth0_token)

    def auth(self, u: AuthenticatedClient) -> dict[str, str]:
        return {"Authorization": f"Bearer {u.token}"}

    def json(self, h: dict[str, str]) -> dict[str, str]:
        return {"Content-Type": "application/json", **h}
