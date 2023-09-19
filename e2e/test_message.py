from typing import Any
from . import base, util
from datetime import datetime, timezone

import requests
import json

class TestMessageEndpoints(base.IntegrationTest):
    messages: list[tuple[str, dict[str, Any]]] = []

    def runTest(self):
        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        # Create a message belonging to u1
        r = requests.post(f"{self.origin}/v2/message", headers=self.auth(u1), json={
            "content": "I'm a magical labrador named Murphy, who are you? ",
        })
        r.raise_for_status()

        msgs = [json.loads(util.last_response_line(r))]
        m1 = msgs[0]
        self.messages.append((m1["id"], u1))
        for c in m1["children"]:
            self.messages.append((c["id"], u1))

        defaults = [
            ("max_tokens", 2048),
            ("temperature", 1.0),
            ("n", 1),
            ("top_p", 1.0),
            ("logprobs", 0),
            ("stop", [])
        ]
        for name, value in defaults:
            assert m1["opts"][name] == value

        # Test inference option validation. Each tuple is of the form:
        # (field_name, invalid_values, valid_values)
        fields = [
            # We don't test values numbers close to most maximums b/c they surpass the thresholds
            # of what our tiny local models can do...
            ("max_tokens",  [0, 1.0, "three", 4097],    [1, 32]),
            ("temperature", [-1.0, "three", 2.1],       [0, 0.5, 1]),
            ("top_p",       [-1, "three", 1.1],         [0.1, 0.5, 1]),

            # TODO: test these cases, once supported (they were disabled when streaming was added)
            ("n",           [-1, 1.0, "three", 51],     []),
            ("logprobs",    [-1, 1.0, "three", 6],      []),
        ]
        for (name, invalid, valid) in fields:
            for v in invalid:
                r = requests.post(f"{self.origin}/v2/message", headers=self.auth(u1), json={
                    "content": f"Testing invalid value \"{v}\" for {name}",
                    "opts": { name: v }
                })
                assert r.status_code == 400, f"Expected 400 for invalid value {v} for {name}"
            for v in valid:
                r = requests.post(f"{self.origin}/v2/message", headers=self.auth(u1), json={
                    "content": f"Testing valid value \"{v}\" for {name}",
                    "opts": { name: v }
                })
                assert r.status_code == 200, f"Expected 200 for valid value {v} for {name}"
                msg = json.loads(util.last_response_line(r))
                self.messages.append((msg["id"], u1))
                for default_name, default_value in defaults:
                    actual = msg["opts"][default_name]
                    expected = v if default_name == name else default_value
                    if actual != expected:
                        raise AssertionError(f"Value for {default_name} was {actual}, expected {expected}")

        # Verify GET /v2/message/:id
        r = requests.get(f"{self.origin}/v2/message/{m1['id']}", headers=self.auth(u1))
        msgs.append(r.json())
        for m in msgs:
            assert m["id"] is not None
            assert m["content"] == "I'm a magical labrador named Murphy, who are you? "
            assert m["creator"] == u1["client"]
            assert m["role"] == "user"
            assert datetime.fromisoformat(m["created"]) <= datetime.now(timezone.utc)
            assert m["deleted"] is None
            assert m["root"] == m["id"]
            assert m["template"] is None
            assert m["logprobs"] is None
            assert len(m["children"]) == 1

        # Check /v2/message/:id works as expected for children
        c1 = m1["children"][0]
        r = requests.get(f"{self.origin}/v2/message/{c1['id']}", headers=self.auth(u1))
        c1 = r.json()
        assert c1["id"] == m1["children"][0]["id"]
        assert c1["parent"] == m1["id"]
        assert c1["children"] is None

        # Make sure that creating messages with parents works as expected
        r = requests.post(f"{self.origin}/v2/message", headers=self.auth(u1), json={
            "content": "Complete this thought: I like ",
            "parent": c1["id"],
        })
        r.raise_for_status()
        c2 = json.loads(util.last_response_line(r))
        self.messages.append((c2["id"], u1))
        for c in c2["children"]:
            self.messages.append((c["id"], u1))
        assert c2["parent"] == c1["id"]
        assert c2["content"] == "Complete this thought: I like "
        assert len(c2["children"]) == 1

        # Verify the full tree
        r = requests.get(f"{self.origin}/v2/message/{m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        expect = [
            (m1["id"], "user", 1),
            (c1["id"], "assistant", 1),
            (c2["id"], "user", 1),
            (c2["children"][0]["id"], "assistant", 0),
        ]
        actual = []
        node = r.json()
        while node is not None:
            actual.append((node["id"], node["role"], len(node["children"]) if node["children"] else 0))
            node = node["children"][0] if node["children"] else None
        assert actual == expect

        # Create a message belonging to u2
        r = requests.post(f"{self.origin}/v2/message", headers=self.auth(u2), json={
            "content": "I'm a wizardly horse named Grasshopper, who are you? ",
        })
        r.raise_for_status()
        m2 = json.loads(util.last_response_line(r))
        self.messages.append((m2["id"], u2))
        for c in m2["children"]:
            self.messages.append((c["id"], u2))

        # Makes sure /v2/messages works. We don't verify that *only* the messages
        # created in this test are returned so that the tests are repeatable w/o a database reset.
        r = requests.get(f"{self.origin}/v2/messages", headers=self.auth(u1))
        r.raise_for_status()
        msgs = r.json()
        ids = [m["id"] for m in msgs]
        assert m1["id"] in ids
        assert m2["id"] in ids
        assert ids.index(m2["id"]) < ids.index(m1["id"])
        for m in msgs:
            r = requests.get(f"{self.origin}/v2/message/{m['id']}", headers=self.auth(u1))
            r.raise_for_status()
            assert r.json() == m

        # List by author
        r = requests.get(f"{self.origin}/v2/messages", headers=self.auth(u1), params={ "creator": u1["client"] })
        r.raise_for_status()
        msgs = r.json()
        ids = [m["id"] for m in msgs]
        assert m1["id"] in ids
        assert m2["id"] not in ids

        r = requests.get(f"{self.origin}/v2/messages", headers=self.auth(u1), params={ "creator": u2["client"] })
        r.raise_for_status()
        msgs = r.json()
        ids = [m["id"] for m in msgs]
        assert m2["id"] in ids
        assert m1["id"] not in ids

        # Make sure u2 can't delete u1
        r = requests.delete(f"{self.origin}/v2/message/{m1['id']}", headers=self.auth(u2))
        assert r.status_code == 403

        # Delete the message
        r = requests.delete(f"{self.origin}/v2/message/{m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        deleted = r.json()["deleted"]
        assert deleted is not None

        # Verify that deletes are idempotent
        r = requests.delete(f"{self.origin}/v2/message/{m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert r.json()["deleted"] == deleted

        # Don't list deleted messages by default
        r = requests.get(f"{self.origin}/v2/messages", headers=self.auth(u1))
        r.raise_for_status()
        msgs = r.json()
        ids = [m["id"] for m in msgs]
        assert m1["id"] not in ids

        # Unless ?deleted is set
        r = requests.get(f"{self.origin}/v2/messages?deleted", headers=self.auth(u1))
        r.raise_for_status()
        msgs = r.json()
        ids = [m["id"] for m in msgs]
        assert m1["id"] in ids
        assert m2["id"] in ids
        assert ids.index(m2["id"]) < ids.index(m1["id"])

    def tearDown(self):
        for (id, user) in self.messages:
            r = requests.delete(f"{self.origin}/v2/message/{id}", headers=self.auth(user))
            r.raise_for_status()

