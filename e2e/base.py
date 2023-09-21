import requests
from typing import Any
from unittest import TestCase

import os

class IntegrationTest(TestCase):
    origin = os.environ.get("ORIGIN", "http://localhost:8000")

    def user(self, email: str) -> dict[str, Any]:
        r = requests.get(f"{self.origin}/v3/whoami", headers={"X-Auth-Request-Email": email})
        r.raise_for_status()
        return r.json()

    def auth(self, u: dict[str, Any]) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + u["token"]
        }

