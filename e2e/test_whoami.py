from . import base

import requests

class TestWhoAmIEndpoints(base.IntegrationTest):

    def runTest(self):
        # Fail w/o auth
        r = requests.get(f"{self.origin}/v3/whoami")
        assert r.status_code == 401

        # Happy path: HTTP cookie
        user = self.user("murphy@allenai.org")
        r = requests.get(f"{self.origin}/v3/whoami", cookies={
            "token": user.token
        })
        r.raise_for_status()

        payload = r.json()
        assert payload["client"] == "murphy@allenai.org"
        assert list(payload.keys()) == ["client"]

        # Happy path: bearer token
        r = requests.get(f"{self.origin}/v3/whoami", headers={
            "Authorization": f"Bearer {user.token}"
        })
        r.raise_for_status()

        payload = r.json()
        assert payload["client"] == "murphy@allenai.org"
        assert list(payload.keys()) == ["client"]

