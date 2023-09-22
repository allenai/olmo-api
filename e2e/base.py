import requests
from unittest import TestCase
from dataclasses import dataclass

import os

@dataclass
class AuthenticatedClient:
    client: str
    token: str

class IntegrationTest(TestCase):
    origin = os.environ.get("ORIGIN", "http://localhost:8000")

    def user(self, email: str) -> AuthenticatedClient:
        r = requests.get(f"{self.origin}/v3/whoami", headers={"X-Auth-Request-Email": email})
        r.raise_for_status()
        token = r.cookies.get("token")
        if token is None:
            raise RuntimeError("no token in cookie")
        client = r.json()["client"]
        return AuthenticatedClient(client, token)

    def auth(self, u: AuthenticatedClient) -> dict[str, str]:
        return { "Authorization": f"Bearer {u.token}" }

