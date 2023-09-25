from . import base, util

import requests
import json
import time

class TestCompletionEndpoints(base.IntegrationTest):

    def runTest(self):
        # Creating login URLS requires auth
        r = requests.post(f"{self.origin}/v3/login")
        assert r.status_code == 401

        # ...and users must be admins
        non_admin = self.user("test1@localhost")
        r = requests.post(f"{self.origin}/v3/login", cookies={
            "token": non_admin.token
        })
        assert r.status_code == 403

        # An admin user who can create login urls
        admin = self.user("sams@allenai.org")

        # Invalid intervals should return a 400
        invalid = [ f"{7 * 24 + 1}h", "0h", "-1h", "1", "1.5h", "1h30m", "1 minute"]
        for expires in invalid:
            r = requests.post(f"{self.origin}/v3/login", cookies={
                "token": admin.token
            }, json={
                "email": "test2@localhost",
                "expires": expires
            })
            assert r.status_code == 400

        # Create a login URL that expires quickly
        r = requests.post(f"{self.origin}/v3/login", cookies={
            "token": admin.token
        }, json={
            "client": "test2@localhost",
            "expires_in": "1s"
        })
        r.raise_for_status()

        time.sleep(1.1)

        url = r.json()["url"]
        r = requests.get(url, allow_redirects=False)
        assert r.status_code == 401

        # Validate the happy path
        r = requests.post(f"{self.origin}/v3/login", cookies={
            "token": admin.token
        }, json={
            "client": "test2@localhost",
            "expires_in": "60s"
        })
        r.raise_for_status()

        url = r.json()["url"]
        r = requests.get(url, allow_redirects=False)
        assert r.status_code == 302

        token = r.cookies.get("token")
        assert token is not None

        r = requests.get(f"{self.origin}/v3/whoami", cookies={
            "token": token
        })
        r.raise_for_status()
        assert r.json()["client"] == "test2@localhost"

        user_client_token = r.cookies.get("token")

        # Make sure auth tokens can't be used as login URLs
        r = requests.get(f"{self.origin}/v3/login/{token}")
        assert r.status_code == 401

        r = requests.get(f"{self.origin}/v3/login/{token}", cookies={
            "token": user_client_token
        })
        assert r.status_code == 409

