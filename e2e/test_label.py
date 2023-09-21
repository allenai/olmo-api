from . import base, util
from datetime import datetime, timezone
from typing import Any

import requests
import json

class TestLabelEndpoints(base.IntegrationTest):
    messages: list[tuple[str, dict[str, Any]]] = []
    labels: list[tuple[str, dict[str, Any]]] = []

    def runTest(self):
        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        # Create a few messages belonging by u1
        content = ["Is Murphy a unicorn?", "Is Murphy Poseidon?"]
        msgs = []
        for c  in content:
            r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={ "content": c })
            r.raise_for_status()
            m = json.loads(util.last_response_line(r))
            self.messages.append((m["id"], u1))
            msgs.append(m)
        m1, m2 = msgs

        # Verify 400s
        bad = [
            { "rating": "nope", "message": m1["id"] },
            { "rating": -20, "message": m1["id"] },
            { "rating": -1, "message": "nope" }
        ]
        for b in bad:
            r = requests.post(f"{self.origin}/v3/label", headers=self.auth(u1), json=b)
            assert r.status_code == 400

        # Create a label
        r = requests.post(f"{self.origin}/v3/label", headers=self.auth(u1), json={
            "rating": 1,
            "message": m1["id"]
        })
        r.raise_for_status()
        l1 = r.json()
        self.labels.append((l1["id"], u1))
        assert l1["id"] is not None
        assert l1["rating"] == 1
        assert l1["message"] == m1["id"]
        assert l1["creator"] == u1["client"]
        assert datetime.fromisoformat(l1["created"]) <= datetime.now(timezone.utc)
        assert l1["deleted"] is None
        assert l1["comment"] is None

        # Make sure /v3/message/:id returns the label
        r = requests.get(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert len(r.json()["labels"]) == 1
        assert r.json()["labels"][0] == l1

        # Make sure /v3/message/:id doesn't return the label for u2
        r = requests.get(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u2))
        r.raise_for_status()
        assert len(r.json()["labels"]) == 0

        # Make sure /messages returns the label
        r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(u1))
        r.raise_for_status()
        for m in r.json()["messages"]:
            if m["id"] != m1["id"]:
                continue
            assert len(m["labels"]) == 1
            assert m["labels"][0] == l1

        # Make sure /messages doesn't return the label for u2
        r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(u2))
        r.raise_for_status()
        for m in r.json()["messages"]:
            if m["id"] != m1["id"]:
                continue
            assert len(m["labels"]) == 0

        # Verify /v3/label/:id
        r = requests.get(f"{self.origin}/v3/label/{l1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert l1 == r.json()

        # Create a duplicate
        r = requests.post(f"{self.origin}/v3/label", headers=self.auth(u1), json={
            "rating": 0,
            "message": m1["id"]
        })
        assert r.status_code == 422

        # Create a label belonging to u2
        r = requests.post(f"{self.origin}/v3/label", headers=self.auth(u2), json={
            "rating": -1,
            "message": m2["id"],
            "comment": "Unicorns are not real"
        })
        r.raise_for_status()
        l2 = r.json()
        self.labels.append((l2["id"], u2))
        assert l2["id"] is not None
        assert l2["rating"] == -1
        assert l2["message"] == m2["id"]
        assert l2["creator" ] == u2["client"]
        assert datetime.fromisoformat(l2["created"]) <= datetime.now(timezone.utc)
        assert l2["deleted"] is None
        assert l2["comment"] == "Unicorns are not real"

        # Verify listing labels
        r = requests.get(f"{self.origin}/v3/labels", headers=self.auth(u1))
        r.raise_for_status()
        ids = [l["id"] for l in r.json()]
        assert l1["id"] in ids
        assert l2["id"] in ids
        assert ids.index(l2["id"]) < ids.index(l1["id"])

        # Verify filtering by message
        r = requests.get(f"{self.origin}/v3/labels?message={m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert r.json() == [l1]

        # Verify filtering by creator
        r = requests.get(f"{self.origin}/v3/labels?creator={u2['client']}", headers=self.auth(u1))
        r.raise_for_status()
        ids = [l["id"] for l in r.json()]
        assert l2["id"] in ids
        assert l1["id"] not in ids

        # Make sure u2 can't delete labels belonging to u1
        r = requests.delete(f"{self.origin}/v3/label/{l1['id']}", headers=self.auth(u2))
        assert r.status_code == 403

        # Delete a label
        r = requests.delete(f"{self.origin}/v3/label/{l1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert r.json()["deleted"] is not None

        # Make sure /v3/message/:id no longer returns it.
        r = requests.get(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert len(r.json()["labels"]) == 0

        # ...and that /v3/messages does the same
        r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(u1))
        r.raise_for_status()
        for m in r.json()["messages"]:
            if m["id"] != m1["id"]:
                continue
            assert len(m["labels"]) == 0

        # Update the deleted label
        r = requests.get(f"{self.origin}/v3/label/{l1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        l1 = r.json()

        # Verify that deleted labels aren't included by default...
        r = requests.get(f"{self.origin}/v3/labels", headers=self.auth(u1))
        r.raise_for_status()
        ids = [l["id"] for l in r.json()]
        assert l1["id"] not in ids

        # Unless deleted is set.
        r = requests.get(f"{self.origin}/v3/labels?deleted", headers=self.auth(u1))
        r.raise_for_status()
        ids = [l["id"] for l in r.json()]
        assert l1["id"] in ids
        assert l2["id"] in ids
        assert ids.index(l2["id"]) < ids.index(l1["id"])

        # And that a user can relabel that message
        r = requests.post(f"{self.origin}/v3/label", headers=self.auth(u1), json={
            "rating": 0,
            "message": m1["id"]
        })
        assert r.status_code == 200
        self.labels.append((r.json()["id"], u1))

    def tearDown(self):
        for (id, user) in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
        for (id, user) in self.labels:
            r = requests.delete(f"{self.origin}/v3/label/{id}", headers=self.auth(user))
            r.raise_for_status()

