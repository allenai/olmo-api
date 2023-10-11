from . import base
from datetime import datetime, timezone

import requests

class TestPromptTemplateEndpoints(base.IntegrationTest):
    # Prompts (and Token belonging to their author) to delete after text execution
    prompts:list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        # Make sure all endpoints require auth
        for r in [
            requests.post(f"{self.origin}/v3/templates/prompt", json={}),
            requests.get(f"{self.origin}/v3/templates/prompts"),
            requests.get(f"{self.origin}/v3/templates/prompt/XXX"),
            requests.patch(f"{self.origin}/v3/templates/prompt/XXX"),
            requests.delete(f"{self.origin}/v3/templates/prompt/XXX")
        ]:
            assert r.status_code == 401

        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        # Verify case where no prompt exists.
        r = requests.get(f"{self.origin}/v3/templates/prompt/notfound", headers=self.auth(u1))
        assert r.status_code == 404

        # Create prompt belonging to u1.
        r = requests.post(f"{self.origin}/v3/templates/prompt", headers=self.auth(u1), json={
            "name": "Test Prompt #1",
            "content": "Murphy is a good dog who likes to "
        })
        r.raise_for_status()
        p1 = r.json()
        self.prompts.append((p1["id"], u1))
        assert p1["id"] is not None
        assert p1["name"] == "Test Prompt #1"
        assert p1["content"] == "Murphy is a good dog who likes to "
        assert p1["author"] == "test1@localhost"
        assert p1["creator"] == "test1@localhost"
        assert datetime.fromisoformat(p1["created"]) < datetime.now(timezone.utc)
        assert datetime.fromisoformat(p1["created"]) == datetime.fromisoformat(p1["updated"])
        assert p1["deleted"] is None

        # Create prompt belonging to u2
        r = requests.post(f"{self.origin}/v3/templates/prompt", headers=self.auth(u2), json={
            "name": "Test Prompt #2",
            "content": "Grasshopper is a silly horse that likes to "
        })
        r.raise_for_status()
        p2 = r.json()
        self.prompts.append((p2["id"], u2))

        # Make sure both prompts are returned. We don't verify that *only* those prompts are
        # returned so that the tests are repeatable w/o a database reset.
        r = requests.get(f"{self.origin}/v3/templates/prompts", headers=self.auth(u1))
        r.raise_for_status()
        prompts = r.json()
        ids = [ p["id"] for p in prompts ]
        assert p1["id"] in ids
        assert p2["id"] in ids
        assert ids.index(p2["id"]) < ids.index(p1["id"])

        # Update p1.
        r = requests.patch(f"{self.origin}/v3/templates/prompt/{p1['id']}", headers=self.auth(u1), json={
            "name": "Test Prompt #1 (updated)",
        })
        r.raise_for_status()
        assert r.json()["name"] == "Test Prompt #1 (updated)"

        # Verify the update
        r = requests.get(f"{self.origin}/v3/templates/prompt/{p1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert r.json()["name"] == "Test Prompt #1 (updated)"
        assert r.json()["updated"] > p1["updated"]

        # Verify u2 can't update the prompt belonging to u1.
        r = requests.patch(f"{self.origin}/v3/templates/prompt/{p1['id']}", headers=self.auth(u2), json={
            "name": "Test Prompt #1 (updated)",
        })
        assert r.status_code == 403

        # Verify u2 can't delete the prompt belonging to u1.
        r = requests.delete(f"{self.origin}/v3/templates/prompt/{p1['id']}", headers=self.json(self.auth(u2)))
        assert r.status_code == 403

        # Delete p1.
        r = requests.patch(f"{self.origin}/v3/templates/prompt/{p1['id']}", headers=self.auth(u1), json={
            "deleted": True,
        })
        r.raise_for_status()
        assert r.json()["deleted"] is not None

        # Update our record of p1, verify deletion.
        r = requests.get(f"{self.origin}/v3/templates/prompt/{p1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        p1 = r.json()
        assert p1["deleted"] is not None

        # Verify that p1 is no longer in the list of prompts.
        r = requests.get(f"{self.origin}/v3/templates/prompts", headers=self.auth(u1))
        r.raise_for_status()
        prompts = r.json()
        ids = [ p["id"] for p in prompts ]
        assert p1["id"] not in ids

        # Verify that ?deleted changes that.
        r = requests.get(f"{self.origin}/v3/templates/prompts?deleted", headers=self.auth(u1))
        r.raise_for_status()
        prompts = r.json()
        ids = [ p["id"] for p in prompts ]
        assert p1["id"] in ids
        assert p2["id"] in ids
        assert ids.index(p1["id"]) < ids.index(p2["id"])

        # Undelete p1
        r = requests.patch(f"{self.origin}/v3/templates/prompt/{p1['id']}", headers=self.auth(u1), json={
            "deleted": False,
        })
        r.raise_for_status()
        assert r.json()["deleted"] is None
        assert r.json()["id"] == p1["id"]
        assert r.json()["updated"] > p1["updated"]
        assert r.json()["name"] == p1["name"]
        assert r.json()["content"] == p1["content"]
        assert r.json()["author"] == p1["author"]
        assert r.json()["creator"] == p1["creator"]

        # Make sure it's back
        r = requests.get(f"{self.origin}/v3/templates/prompts", headers=self.auth(u1))
        r.raise_for_status()
        prompts = r.json()
        ids = [ p["id"] for p in prompts ]
        assert p1["id"] in ids

        # Verify DELETE instead of PATCH
        r = requests.delete(f"{self.origin}/v3/templates/prompt/{p1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert r.json()["deleted"] is not None
        assert r.json()["updated"] > p1["updated"]

        # Make sure it's gone again
        r = requests.get(f"{self.origin}/v3/templates/prompts", headers=self.auth(u1))
        r.raise_for_status()
        prompts = r.json()
        ids = [ p["id"] for p in prompts ]
        assert p1["id"] not in ids

        # Make sure a patch doesn't undelete it
        r = requests.patch(f"{self.origin}/v3/templates/prompt/{p1['id']}", headers=self.auth(u1), json={
            "name": "Test Prompt #1 (updated again!)",
        })
        r.raise_for_status()
        assert r.json()["deleted"] is not None
        assert r.json()["updated"] > p1["updated"]
        assert r.json()["name"] == "Test Prompt #1 (updated again!)"

    def tearDown(self):
        for (id, user) in self.prompts:
            r = requests.delete(f"{self.origin}/v3/templates/prompt/{id}", headers=self.auth(user))
            r.raise_for_status()

