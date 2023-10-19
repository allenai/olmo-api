from . import base, util

import requests
import json

class TestMessageDatachips(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []
    datachips: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        u1 = self.user("test1@localhost")

        # Create a datachip
        r = requests.post(f"{self.origin}/v3/datachip", json={
            "name": "Dog",
            "content": "Murphy"
        }, headers=self.auth(u1))
        r.raise_for_status()
        dc1 = r.json()
        self.datachips.append((dc1["id"], u1))

        # Create a message w/ the chip
        r = requests.post(f"{self.origin}/v3/message", json={
            "content": f"""<span data-datachip-id="{dc1["id"]}">{dc1["name"]}</span> is a dog. Can he fly?"""
        }, headers=self.auth(u1))
        r.raise_for_status()
        msg1 = json.loads(util.last_response_line(r))
        self.messages.append((msg1["id"], u1))
        assert msg1["content"] == f"""<span data-datachip-id="{dc1["id"]}">{dc1["name"]}</span> is a dog. Can he fly?"""

        r = requests.get(f"{self.origin}/v3/completion/{msg1['children'][0]['completion']}", headers=self.auth(u1))
        r.raise_for_status()
        comp1 = r.json()
        assert comp1["input"] == f"""
<|user|>
Murphy is a dog. Can he fly?
""".strip()

        # Create another chip.
        r = requests.post(f"{self.origin}/v3/datachip", json={
            "name": "Friend",
            "content": "Grasshopper"
        }, headers=self.auth(u1))
        r.raise_for_status()
        dc2 = r.json()
        self.datachips.append((dc2["id"], u1))

        # Create another message w/ the chip
        r = requests.post(f"{self.origin}/v3/message", json={
            "content": f"""<span data-datachip-id="{dc2["id"]}">{dc2["name"]}</span> is <span data-datachip-id="{dc1["id"]}">{dc1["name"]}</span>'s friend. Can she fly?""",
            "parent": msg1["children"][0]["id"]
        }, headers=self.auth(u1))
        r.raise_for_status()
        msg2 = json.loads(util.last_response_line(r))
        self.messages.append((msg2["id"], u1))

        r = requests.get(f"{self.origin}/v3/completion/{msg2['children'][0]['completion']}", headers=self.auth(u1))
        r.raise_for_status()
        comp2 = r.json()
        assert comp2["input"] == f"""
<|user|>
Murphy is a dog. Can he fly?
<|assistant|>
{comp1["outputs"][0]["text"]}
<|user|>
Grasshopper is Murphy's friend. Can she fly?
""".strip()

    def tearDown(self):
        for (id, user) in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
        for (id, user) in self.datachips:
            r = requests.patch(f"{self.origin}/v3/datachip/{id}", json={ "deleted": True }, headers=self.auth(user))
            r.raise_for_status()


