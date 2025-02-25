from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import requests

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
        assert payload["termsAcceptedDate"] == terms_accepted_date.astimezone(UTC).isoformat()

        # whoami should return that the user has accepted T&Cs
        r = requests.get(url=f"{self.origin}/v3/whoami", cookies={"token": user.token})
        payload = r.json()
        assert payload["hasAcceptedTermsAndConditions"] is True

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
        assert payload["termsAcceptedDate"] == terms_accepted_date.astimezone(UTC).isoformat()
        assert payload["acceptanceRevokedDate"] == acceptance_revoked_date.astimezone(UTC).isoformat()

        # whoami should return that the user has not accepted T&Cs if they've revoked
        r = requests.get(url=f"{self.origin}/v3/whoami", cookies={"token": user.token})
        payload = r.json()
        assert payload["hasAcceptedTermsAndConditions"] is False

        new_terms_accepted_date = datetime.now(ZoneInfo("America/Los_Angeles"))

        # Happy path: Creates user if it doesn't exist
        r = requests.put(
            f"{self.origin}/v3/user",
            cookies={"token": user.token},
            json={"termsAcceptedDate": new_terms_accepted_date.isoformat()},
        )
        r.raise_for_status()

        payload = r.json()
        assert payload["termsAcceptedDate"] == new_terms_accepted_date.astimezone(UTC).isoformat()
        assert payload["acceptanceRevokedDate"] == acceptance_revoked_date.astimezone(UTC).isoformat()

        # whoami should return that the user has accepted T&Cs if they've revoked acceptance then accepted again later
        r = requests.get(url=f"{self.origin}/v3/whoami", cookies={"token": user.token})
        payload = r.json()
        assert payload["hasAcceptedTermsAndConditions"] is True
