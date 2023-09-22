from . import base
from datetime import datetime, timezone

import requests

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

        assert payload["client"] == "murphy@allenai.org"
        assert list(payload.keys()) == ["client"]

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

        # Reuse token in cookie
        r = requests.get(f"{self.origin}/v3/whoami", cookies={
            "token": cookie.value
        })
        r.raise_for_status()

        new_cookies = [ c for c in r.cookies if c.name == "token" ]
        assert len(new_cookies) == 1

        assert new_cookies[0].value == cookie.value
        assert new_cookies[0].expires == cookie.expires
        assert new_cookies[0].secure == cookie.secure
        assert new_cookies[0].get_nonstandard_attr("SameSite") == cookie.get_nonstandard_attr("SameSite")
        assert new_cookies[0].has_nonstandard_attr("HttpOnly") == cookie.has_nonstandard_attr("HttpOnly")

        # Reuse token in header
        r = requests.get(f"{self.origin}/v3/whoami", headers={
            "Authorization": f"Bearer {cookie.value}"
        })
        r.raise_for_status()

        new_cookies = [ c for c in r.cookies if c.name == "token" ]
        assert new_cookies[0].value == cookie.value

        # Use token over email
        r = requests.get(f"{self.origin}/v3/whoami", cookies={
            "token": cookie.value
        }, headers={
            "X-Auth-Request-Email": "murphy@allenai.org"
        })
        r.raise_for_status()

        new_cookies = [ c for c in r.cookies if c.name == "token" ]
        assert new_cookies[0].value == cookie.value

