from . import base, util
from datetime import datetime, timezone

import requests
import json

class TestMessageEndpoints(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        # Make sure all endpoints fail w/o auth
        for r in [
            requests.get(f"{self.origin}/v3/messages"),
            requests.post(f"{self.origin}/v3/message", json={}),
            requests.get(f"{self.origin}/v3/message/XXX"),
            requests.delete(f"{self.origin}/v3/message/XXX"),
        ]:
            assert r.status_code == 401

        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        # Create a message belonging to u1
        r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
            "content": "I'm a magical labrador named Murphy, who are you? ",
        })
        r.raise_for_status()

        msgs = [json.loads(util.last_response_line(r))]
        m1 = msgs[0]
        self.messages.append((m1["id"], u1))
        for c in m1["children"]:
            self.messages.append((c["id"], u1))

        # Create a message w/ logprobs
        r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
            "content": "why are labradors smarter than unicorns?",
            "opts": {
                "logprobs": 2
            }
        })
        r.raise_for_status()
        lines = list(r.text.splitlines())
        for line in lines[1:-1]:
            chunk = json.loads(line)
            assert all(len(lp) == 2 for lp in chunk.get("logprobs", []))
        final = json.loads(lines[-1])
        self.messages.append((final["id"], u1))
        assert all(len(lp) == 2 for lp in final.get("logprobs", []))
        assert isinstance(final["children"][0]["logprobs"][0].get("text"), str)
        assert isinstance(final["children"][0]["logprobs"][0].get("token_id"), int) >= 0 and final["logprobs"][0].get("token_id") >= 0
        assert isinstance(final["children"][0]["logprobs"][0].get("logprob"), float)
        assert final["logprobs"][0].get("logprob") > final["logprobs"][1].get("logprob")

        msgs = [json.loads(util.last_response_line(r))]
        m1 = msgs[0]
        self.messages.append((m1["id"], u1))
        for c in m1["children"]:
            self.messages.append((c["id"], u1))

        defaults = [
            ("max_tokens", 2048),
            ("temperature", 0.5),
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
            ("logprobs",    [-1, 1.0, "three", 11],     [0, 1, 10]),
        ]
        for (name, invalid, valid) in fields:
            for v in invalid:
                r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
                    "content": f"Testing invalid value \"{v}\" for {name}",
                    "opts": { name: v }
                })
                assert r.status_code == 400, f"Expected 400 for invalid value {v} for {name}"
            for v in valid:
                # top_p can only be set to a value that isn't 1.0 if temperature is > 0
                opts = { name: v }
                if name == "top_p" and v != 1.0:
                    opts["temperature"] = 0.5

                r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
                    "content": f"Testing valid value \"{v}\" for {name}",
                    "opts": opts
                })
                assert r.status_code == 200, f"Expected 200 for valid value {v} for {name}"
                msg = json.loads(util.last_response_line(r))
                self.messages.append((msg["id"], u1))
                for default_name, default_value in defaults:
                    actual = msg["opts"][default_name]
                    expected = opts.get(default_name, default_value)
                    if actual != expected:
                        raise AssertionError(f"Value for {default_name} was {actual}, expected {expected}")

        # Verify GET /v3/message/:id
        r = requests.get(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        msgs.append(r.json())
        for m in msgs:
            assert m["id"] is not None
            assert m["content"] == "I'm a magical labrador named Murphy, who are you? "
            assert m["creator"] == u1.client
            assert m["role"] == "user"
            assert datetime.fromisoformat(m["created"]) <= datetime.now(timezone.utc)
            assert m["deleted"] is None
            assert m["root"] == m["id"]
            assert m["template"] is None
            assert m["logprobs"] is None
            assert m["private"] is False
            assert len(m["children"]) == 1

        # Check /v3/message/:id works as expected for children
        c1 = m1["children"][0]
        r = requests.get(f"{self.origin}/v3/message/{c1['id']}", headers=self.auth(u1))
        c1 = r.json()
        assert c1["id"] == m1["children"][0]["id"]
        assert c1["parent"] == m1["id"]
        assert c1["children"] is None

        # Make sure that creating messages with parents works as expected
        r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
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
        r = requests.get(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
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
        r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u2), json={
            "content": "I'm a wizardly horse named Grasshopper, who are you? ",
        })
        r.raise_for_status()
        m2 = json.loads(util.last_response_line(r))
        self.messages.append((m2["id"], u2))
        for c in m2["children"]:
            self.messages.append((c["id"], u2))

        # Verify listing messages
        r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(u1))
        r.raise_for_status()
        msglist = r.json()
        assert msglist["meta"]["total"] > 0
        assert msglist["meta"]["offset"] == 0
        assert msglist["meta"]["limit"] == 10
        ids = [m["id"] for m in msglist["messages"]]
        assert m1["id"] in ids
        assert m2["id"] in ids
        assert ids.index(m2["id"]) < ids.index(m1["id"])
        for m in msglist["messages"]:
            r = requests.get(f"{self.origin}/v3/message/{m['id']}", headers=self.auth(u1))
            r.raise_for_status()
            assert r.json() == m

        r = requests.get(f"{self.origin}/v3/messages?offset=1", headers=self.auth(u1))
        r.raise_for_status()
        offset_msglist = r.json()
        assert offset_msglist["meta"]["total"] > 0
        assert offset_msglist["meta"]["offset"] == 1
        assert offset_msglist["meta"]["limit"] == 10
        offset_ids = [m["id"] for m in offset_msglist["messages"]]
        assert msglist["messages"][0]["id"] not in offset_ids
        for m in msglist["messages"][1:]:
            assert m["id"] in offset_ids
        assert m1["id"] in ids
        assert m2["id"] in ids
        assert ids.index(m2["id"]) < ids.index(m1["id"])

        r = requests.get(f"{self.origin}/v3/messages?offset=1&limit=1", headers=self.auth(u1))
        r.raise_for_status()
        limit_msglist = r.json()
        assert limit_msglist["meta"]["total"] > 0
        assert limit_msglist["meta"]["offset"] == 1
        assert limit_msglist["meta"]["limit"] == 1
        assert len(limit_msglist["messages"]) == 1
        assert limit_msglist["messages"][0]["id"] == offset_msglist["messages"][0]["id"]

        # List by author
        r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(u1), params={ "creator": u1.client })
        r.raise_for_status()
        u1_msglist = r.json()
        assert u1_msglist["meta"]["total"] > 0
        assert u1_msglist["meta"]["total"] < msglist["meta"]["total"]
        ids = [m["id"] for m in u1_msglist["messages"]]
        assert m1["id"] in ids
        assert m2["id"] not in ids

        r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(u1), params={ "creator": u2.client })
        r.raise_for_status()
        u2_msglist = r.json()
        assert u2_msglist["meta"]["total"] > 0
        assert u2_msglist["meta"]["total"] < msglist["meta"]["total"]
        ids = [m["id"] for m in u2_msglist["messages"]]
        assert m1["id"] not in ids
        assert m2["id"] in ids

        # Make sure u2 can't delete u1
        r = requests.delete(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u2))
        assert r.status_code == 403

        # Delete the message
        r = requests.delete(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        deleted = r.json()["deleted"]
        assert deleted is not None

        # Verify that deletes are idempotent
        r = requests.delete(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert r.json()["deleted"] == deleted

        # Don't list deleted messages by default
        r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(u1))
        r.raise_for_status()
        msglist = r.json()
        ids = [m["id"] for m in msglist["messages"]]
        assert m1["id"] not in ids

        # Unless ?deleted is set
        r = requests.get(f"{self.origin}/v3/messages?deleted", headers=self.auth(u1))
        r.raise_for_status()
        msglist = r.json()
        ids = [m["id"] for m in msglist["messages"]]
        assert m1["id"] in ids
        assert m2["id"] in ids
        assert ids.index(m2["id"]) < ids.index(m1["id"])

        # Test snippet creation
        cases = [
            # Short, valid
            ("Can <em>Murphy</em> dance?", "Can Murphy dance?"),
            # Short, no-close
            ("Can <em>Murphy dance?", "Can Murphy dance?"),
            # Short, no-open
            ("Can Murphy</em> dance?", "Can Murphy dance?"),
            # Long, valid
            (
                "Can <em>Murphy</em> dance after eating <marquee>three thousand hamburgers</marquee> made by a <strong>Grasshopper</strong> on a bright, sunny October afternoon?",
                "Can Murphy dance after eating three thousand hamburgers made by a Grasshopper on a bright, sunny…",
            )
        ]
        for (content, snippet) in cases:
            r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={ "content": content })
            r.raise_for_status()
            m = json.loads(util.last_response_line(r))
            self.messages.append((m["id"], u1))
            assert m["snippet"] == snippet

    def tearDown(self):
        for (id, user) in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()

