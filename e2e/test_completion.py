from . import base, util

import requests
import json

class TestCompletionEndpoints(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        # Make sure all endpoints fail w/o auth
        for r in [
            requests.get(f"{self.origin}/v3/completion/XXX"),
        ]:
            assert r.status_code == 401

        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
            "content": "Is Grasshopper a unicorn?",
        })
        r.raise_for_status()
        m = json.loads(util.last_response_line(r))
        self.messages.append((m["id"], u1))

        # TODO: for now we just make sure the completions exist. We anticipate moving these (soonish)
        # to InferD. We can more rigorously test things then.
        r = requests.get(f"{self.origin}/v3/completion/{m['children'][0]['completion']}", headers=self.auth(u2))
        r.raise_for_status()

    def tearDown(self):
        for (id, user) in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()

