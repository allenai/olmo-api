from datetime import datetime, timezone

import requests
from zoneinfo import ZoneInfo

from . import base


class TestUserEndpoints(base.IntegrationTest):
    def runTest(self):
        # Fail w/o auth
        r = requests.put(f"{self.origin}/v3/user")
        assert r.status_code == 401

        user = self.user("murphy@allenai.org")

        terms_accepted_date = datetime.now(ZoneInfo("America/Los_Angeles"))

        # Happy path: Creates user if it doesn't exist
        r = requests.put(
            f"{self.origin}/v3/user",
            cookies={"token": user.token},
            json={"termsAcceptedDate": terms_accepted_date.isoformat()},
        )
        r.raise_for_status()

        payload = r.json()
        assert payload["client"] == "murphy@allenai.org"
        assert (
            payload["termsAcceptedDate"]
            == terms_accepted_date.astimezone(timezone.utc).isoformat()
        )

        acceptance_revoked_date = datetime.now(ZoneInfo("America/Los_Angeles"))
        # Happy path: Updates an existing user
        r = requests.put(
            f"{self.origin}/v3/user",
            cookies={"token": user.token},
            json={
                "acceptanceRevokedDate": acceptance_revoked_date.isoformat(),
            },
        )
        r.raise_for_status()

        payload = r.json()
        assert payload["client"] == "murphy@allenai.org"
        assert (
            payload["termsAcceptedDate"]
            == terms_accepted_date.astimezone(timezone.utc).isoformat()
        )
        assert (
            payload["acceptanceRevokedDate"]
            == acceptance_revoked_date.astimezone(timezone.utc).isoformat()
        )
