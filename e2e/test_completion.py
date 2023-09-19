from . import base, util
from typing import Any

import requests
import json

class TestCompletionEndpoints(base.IntegrationTest):
    messages: list[tuple[str, dict[str, Any]]] = []

    def runTest(self):
        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        r = requests.post(f"{self.origin}/v2/message", headers=self.auth(u1), json={
            "content": "Is Grasshopper a unicorn?",
            # TODO: restore when n > 1 is supported
            # "opts": { "n": 2 }
        })
        r.raise_for_status()
        m = json.loads(util.last_response_line(r))
        self.messages.append((m["id"], u1))

        r = requests.get(f"{self.origin}/v2/completions", headers=self.auth(u2))
        r.raise_for_status()
        completions = [ c["id"] for c in r.json() ]
        for c in m["children"]:
            assert c["completion"] in completions
        assert len(set([ c["completion"] for c in m["children"] ])) == 1

    def tearDown(self):
        for (id, user) in self.messages:
            r = requests.delete(f"{self.origin}/v2/message/{id}", headers=self.auth(user))
            r.raise_for_status()

