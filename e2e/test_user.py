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
            json={"termsAcceptedDate": terms_accepted_date},
        )
        r.raise_for_status()

        payload = r.json()
        assert payload["client"] == "murphy@allenai.org"
        assert (
            payload["terms_accepted_date"]
            == terms_accepted_date.replace(tzinfo=timezone.utc).isoformat()
        )

        acceptance_revoked_date = datetime.now(ZoneInfo("America/Los_Angeles"))
        # Happy path: Updates an existing user
        r = requests.put(
            f"{self.origin}/v3/user",
            cookies={"token": user.token},
            json={
                "acceptance_revoked_date": acceptance_revoked_date,
            },
        )
        r.raise_for_status()

        payload = r.json()
        assert payload["client"] == "murphy@allenai.org"
        assert (
            payload["terms_accepted_date"]
            == terms_accepted_date.replace(tzinfo=timezone.utc).isoformat()
        )
        assert (
            payload["acceptance_revoked_date"]
            == acceptance_revoked_date.replace(tzinfo=timezone.utc).isoformat()
        )
