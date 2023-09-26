from . import base
from datetime import datetime, timezone

import requests

class TestLoginEndpoints(base.IntegrationTest):

    def runTest(self):
        # Fail w/o auth; users should never get this far since Skiff Login's
        # OAuth proxy should intercept
        r = requests.get(f"{self.origin}/v3/login/skiff")
        assert r.status_code == 500

        # Happy path: bounce the user to the UI and set a cookie
        r = requests.get(f"{self.origin}/v3/login/skiff", headers={
            "X-Auth-Request-Email": "murphy@allenai.org"
        }, allow_redirects=False)
        r.raise_for_status()

        assert r.status_code == 302
        assert r.headers["Location"] == "http://localhost:8080"

        cookies = [ c for c in r.cookies if c.name == "token" ]
        assert len(cookies) == 1

        cookie = cookies[0]
        assert cookie.value is not None

        # Verify expires in 24 hours; tolerate 1 second of error
        assert cookie.expires is not None
        expires = datetime.fromtimestamp(cookie.expires, timezone.utc)
        expires_in = expires - datetime.now(timezone.utc)
        assert 24 * 60 * 60 - expires_in.total_seconds() <= 1

        assert cookie.secure is True
        assert cookie.get_nonstandard_attr("SameSite") == "Strict"
        assert cookie.has_nonstandard_attr("HttpOnly") is True

