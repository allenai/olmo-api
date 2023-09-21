from . import base
from datetime import datetime, timezone

import requests
import time

class TestAuth(base.IntegrationTest):

    def runTest(self):
        # Fail w/o auth
        r = requests.get(f"{self.origin}/v3/whoami")
        assert r.status_code == 401

        # Use email
        r = requests.get(f"{self.origin}/v3/whoami", headers={
            "X-Auth-Request-Email": "murphy@allenai.org"
        })
        r.raise_for_status()

        payload = r.json()

        # Verify expires in 24 hours; tolerate 1 second of error
        expires = datetime.fromisoformat(payload["expires"])
        expires_in = expires - datetime.now(timezone.utc)
        assert 24 * 60 * 60 - expires_in.total_seconds() <= 1

        assert payload["client"] == "murphy@allenai.org"
        assert datetime.fromisoformat(payload["created"]) <= datetime.now(timezone.utc)
        assert payload["token"] is not None and len(payload["token"]) > 0

        cookies = [ c for c in r.cookies if c.name == "token" ]
        assert len(cookies) == 1

        cookie = cookies[0]
        assert cookie.value is not None
        assert cookie.value == payload["token"]
        assert cookie.expires == time.mktime(expires.timetuple())
        assert cookie.secure is True
        assert cookie.get_nonstandard_attr("SameSite") == "Strict"
        assert cookie.has_nonstandard_attr("HttpOnly") is True

        # Reuse token in cookie
        r = requests.get(f"{self.origin}/v3/whoami", cookies={
            "token": cookie.value
        })
        r.raise_for_status()

        assert r.json()["token"] == cookie.value

        # Reuse token in header
        r = requests.get(f"{self.origin}/v3/whoami", headers={
            "Authorization": f"Bearer {payload['token']}"
        })
        r.raise_for_status()

        assert r.json()["token"] == payload['token']

        # Use token over email
        r = requests.get(f"{self.origin}/v3/whoami", cookies={
            "token": cookie.value
        }, headers={
            "X-Auth-Request-Email": "murphy@allenai.org"
        })
        r.raise_for_status()

        assert r.json()["token"] == cookie.value









