import json
from datetime import UTC, datetime

import requests

from . import base, util


class TestMessageDatachips(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []
    datachips: list[tuple[str, base.AuthenticatedClient]] = []
    child_msgs: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        # Deleted datachip refs can't be reused, which means we need to prefix names used in this test.
        prefix = f"{type(self).__name__}_{datetime.now(UTC).strftime('%s')}_"

        # The user must be an admin for this test to work.
        u1 = self.user("murphy@localhost")

        # Create a datachip
        name1 = f"{prefix}Dog"
        r = requests.post(
            f"{self.origin}/v3/datachip", json={"name": name1, "content": "Murphy"}, headers=self.auth(u1)
        )
        r.raise_for_status()
        dc1 = r.json()
        self.datachips.append((dc1["id"], u1))

        # Create a message w/ the chip
        r = requests.post(
            f"{self.origin}/v3/message",
            json={"content": f""":murphy@localhost/{name1} is a dog. Can he fly?"""},
            headers=self.auth(u1),
        )
        r.raise_for_status()
        msg1 = json.loads(util.last_response_line(r))
        self.messages.append((msg1["id"], u1))
        assert msg1["content"] == f""":murphy@localhost/{name1} is a dog. Can he fly?"""

        r = requests.get(f"{self.origin}/v3/completion/{msg1['children'][0]['completion']}", headers=self.auth(u1))
        r.raise_for_status()
        comp1 = r.json()
        assert (
            comp1["input"]
            == """
<|user|>
Murphy is a dog. Can he fly?
""".strip()
        )

        # Create another chip.
        name2 = f"{prefix}Friend"
        r = requests.post(
            f"{self.origin}/v3/datachip", json={"name": name2, "content": "Grasshopper"}, headers=self.auth(u1)
        )
        r.raise_for_status()
        dc2 = r.json()
        self.datachips.append((dc2["id"], u1))

        # Create another message w/ the chip
        r = requests.post(
            f"{self.origin}/v3/message",
            json={
                "content": f""":murphy@localhost/{name2} is :murphy@localhost/{name1}'s friend. Can she fly?""",
                "parent": msg1["children"][0]["id"],
            },
            headers=self.auth(u1),
        )
        r.raise_for_status()
        msg2 = json.loads(util.last_response_line(r))
        c_tup = (msg2["id"], u1)
        self.messages.append(c_tup)
        self.child_msgs.append(c_tup)

        r = requests.get(f"{self.origin}/v3/completion/{msg2['children'][0]['completion']}", headers=self.auth(u1))
        r.raise_for_status()
        comp2 = r.json()
        assert (
            comp2["input"]
            == f"""
<|user|>
Murphy is a dog. Can he fly?
<|assistant|>
{comp1["outputs"][0]["text"]}
<|user|>
Grasshopper is Murphy's friend. Can she fly?
""".strip()
        )

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        self.messages = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
        for id, user in self.datachips:
            r = requests.patch(f"{self.origin}/v3/datachip/{id}", json={"deleted": True}, headers=self.auth(user))
            r.raise_for_status()
