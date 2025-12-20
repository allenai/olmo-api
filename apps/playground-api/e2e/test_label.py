import json
from datetime import UTC, datetime

import pytest
import requests

from . import base, util


class TestLabelEndpoints(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []
    labels: list[tuple[str, base.AuthenticatedClient]] = []

    @pytest.mark.skip(reason="Need to update for the new auth")
    def runTest(self):
        # Make sure all endpoints require auth
        for r in [
            requests.post(f"{self.origin}/v3/label", json={}),
            requests.get(f"{self.origin}/v3/labels"),
            requests.get(f"{self.origin}/v3/label/XXX"),
            requests.delete(f"{self.origin}/v3/label/XXX"),
        ]:
            assert r.status_code == 401

        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        # Create a few messages belonging by u1
        content = ["Is Murphy a unicorn?", "Is Murphy Poseidon?"]
        msgs = []
        for c in content:
            r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={"content": c})
            r.raise_for_status()
            m = json.loads(util.last_response_line(r))
            self.messages.append((m["id"], u1))
            msgs.append(m)
        m1, m2 = msgs

        # Verify 400s
        bad = [
            {"rating": "nope", "message": m1["id"]},
            {"rating": -20, "message": m1["id"]},
            {"rating": -1, "message": "nope"},
        ]
        for b in bad:
            r = requests.post(f"{self.origin}/v3/label", headers=self.auth(u1), json=b)
            assert r.status_code == 400

        # Create a label
        r = requests.post(f"{self.origin}/v3/label", headers=self.auth(u1), json={"rating": 1, "message": m1["id"]})
        r.raise_for_status()
        l1 = r.json()
        self.labels.append((l1["id"], u1))
        assert l1["id"] is not None
        assert l1["rating"] == 1
        assert l1["message"] == m1["id"]
        assert l1["creator"] == u1.client
        assert datetime.fromisoformat(l1["created"]) <= datetime.now(UTC)
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

        # Verify /v3/label/:id
        r = requests.get(f"{self.origin}/v3/label/{l1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert l1 == r.json()

        # Create a duplicate
        r = requests.post(f"{self.origin}/v3/label", headers=self.auth(u1), json={"rating": 0, "message": m1["id"]})
        assert r.status_code == 422

        # Create a label belonging to u2
        r = requests.post(
            f"{self.origin}/v3/label",
            headers=self.auth(u2),
            json={"rating": -1, "message": m2["id"], "comment": "Unicorns are not real"},
        )
        r.raise_for_status()
        l2 = r.json()
        self.labels.append((l2["id"], u2))
        assert l2["id"] is not None
        assert l2["rating"] == -1
        assert l2["message"] == m2["id"]
        assert l2["creator"] == u2.client
        assert datetime.fromisoformat(l2["created"]) <= datetime.now(UTC)
        assert l2["deleted"] is None
        assert l2["comment"] == "Unicorns are not real"

        # Verify listing labels
        r = requests.get(f"{self.origin}/v3/labels", headers=self.auth(u1))
        r.raise_for_status()
        resp = r.json()
        ids = [l["id"] for l in resp["labels"]]
        assert l1["id"] in ids
        assert l2["id"] in ids
        assert ids.index(l2["id"]) < ids.index(l1["id"])
        assert resp["meta"]["total"] > 0
        assert resp["meta"]["offset"] == 0
        assert resp["meta"]["limit"] == 10
        assert resp["meta"]["sort"]["field"] == "created"
        assert resp["meta"]["sort"]["direction"] == "DESC"
        assert resp["labels"].index(l2) < resp["labels"].index(l1)

        # Verify sorting
        r = requests.get(f"{self.origin}/v3/labels", headers=self.auth(u1), params={"sort": "created", "order": "asc"})
        r.raise_for_status()
        resp = r.json()
        assert resp["meta"]["sort"]["field"] == "created"
        assert resp["meta"]["sort"]["direction"] == "ASC"
        assert resp["labels"].index(l1) < resp["labels"].index(l2)

        # Make sure order is implicitly DESC
        r = requests.get(f"{self.origin}/v3/labels", headers=self.auth(u1), params={"sort": "created"})
        r.raise_for_status()
        resp = r.json()
        assert resp["meta"]["sort"]["field"] == "created"
        assert resp["meta"]["sort"]["direction"] == "DESC"
        assert resp["labels"].index(l2) < resp["labels"].index(l1)

        # Make sure invalid sorts return a 400
        for sort, order in [("; drop table", "asc"), ("created", "; drop table"), (None, "asc")]:
            r = requests.get(f"{self.origin}/v3/labels", headers=self.auth(u1), params={"sort": sort, "order": order})
            assert r.status_code == 400

        # Verify pagination
        for case in [{"offset": 0, "limit": 1, "ids": [l2["id"]]}, {"offset": 1, "limit": 1, "ids": [l1["id"]]}]:
            r = requests.get(
                f"{self.origin}/v3/labels?offset={case['offset']}&limit={case['limit']}", headers=self.auth(u1)
            )
            r.raise_for_status()
            resp = r.json()
            assert len(resp["labels"]) == 1
            assert resp["labels"][0]["id"] == case["ids"][0]
            assert resp["meta"]["total"] > 0
            assert resp["meta"]["offset"] == case["offset"]
            assert resp["meta"]["limit"] == case["limit"]

        # Verify filtering by message
        r = requests.get(f"{self.origin}/v3/labels?message={m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert r.json()["labels"] == [l1]

        # Verify filtering by creator
        r = requests.get(f"{self.origin}/v3/labels?creator={u2.client}", headers=self.auth(u1))
        r.raise_for_status()
        ids = [l["id"] for l in r.json()["labels"]]
        assert l2["id"] in ids
        assert l1["id"] not in ids

        # Verify filtering by rating
        r = requests.get(f"{self.origin}/v3/labels?rating=-1", headers=self.auth(u1))
        r.raise_for_status()
        ids = [l["id"] for l in r.json()["labels"]]
        assert l2["id"] in ids
        assert l1["id"] not in ids

        # Bad ratings should return a 400
        r = requests.get(f"{self.origin}/v3/labels?rating=threeve", headers=self.auth(u1))
        assert r.status_code == 400

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

        # Update the deleted label
        r = requests.get(f"{self.origin}/v3/label/{l1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        l1 = r.json()

        # Verify that deleted labels aren't included by default...
        r = requests.get(f"{self.origin}/v3/labels", headers=self.auth(u1))
        r.raise_for_status()
        ids = [l["id"] for l in r.json()["labels"]]
        assert l1["id"] not in ids

        # Unless deleted is set.
        r = requests.get(f"{self.origin}/v3/labels?deleted", headers=self.auth(u1))
        r.raise_for_status()
        ids = [l["id"] for l in r.json()["labels"]]
        assert l1["id"] in ids
        assert l2["id"] in ids
        assert ids.index(l2["id"]) < ids.index(l1["id"])

        # And that a user can relabel that message
        r = requests.post(f"{self.origin}/v3/label", headers=self.auth(u1), json={"rating": 0, "message": m1["id"]})
        assert r.status_code == 200
        self.labels.append((r.json()["id"], u1))

        # Make sure message deletion cascades to labels
        r = requests.delete(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        assert r.status_code == 200
        r = requests.get(f"{self.origin}/v3/label/{l1['id']}", headers=self.auth(u1))
        assert r.status_code == 404
        self.messages = [m for m in self.messages if m[0] != m1["id"]]

    def tearDown(self):
        # Since message deletion cascades, deleting messages should delete their related labels automatically
        for id, user in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
