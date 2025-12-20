import json

import pytest
import requests

from . import base, util


class TestCompletionEndpoints(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []

    @pytest.mark.skip(reason="Completions don't have a new admin model yet")
    def runTest(self):
        u1 = self.user("test1@localhost")

        # Make sure all endpoints fail w/o auth and for non-admins
        for r, status in [
            (requests.get(f"{self.origin}/v3/completion/XXX"), 401),
            (requests.get(f"{self.origin}/v3/completion/XXX", headers=self.auth(u1)), 403),
        ]:
            assert r.status_code == status

        a1 = self.user("murphy@localhost")
        r = requests.post(
            f"{self.origin}/v3/message",
            headers=self.auth(a1),
            json={
                "content": "Is Grasshopper a unicorn?",
            },
        )
        r.raise_for_status()
        m = json.loads(util.last_response_line(r))
        self.messages.append((m["id"], a1))

        # TODO: for now we just make sure the completions exist. We anticipate moving these (soonish)
        # to InferD. We can more rigorously test things then.
        r = requests.get(f"{self.origin}/v3/completion/{m['children'][0]['completion']}", headers=self.auth(a1))
        r.raise_for_status()

    def tearDown(self):
        for id, user in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
