from . import base
from datetime import datetime

import requests

class TestDatachipEndpoints(base.IntegrationTest):
    chips: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        # Make sure all endpoints require auth
        for r in [
            requests.post(f"{self.origin}/v3/datachip", json={}),
            requests.get(f"{self.origin}/v3/datachips"),
            requests.patch(f"{self.origin}/v3/datachip/XXX"),
        ]:
            assert r.status_code == 401

        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        # Must specify a name
        empty = [ "", "   "]
        for name in empty:
            r = requests.post(f"{self.origin}/v3/datachip", headers=self.auth(u1), json={
                "name": name
            })
            assert r.status_code == 400

        # Must specify content
        for content in empty:
            r = requests.post(f"{self.origin}/v3/datachip", headers=self.auth(u1), json={
                "name": "test",
                "content": content
            })
            assert r.status_code == 400

        # Content must be <= 500MB
        r = requests.post(f"{self.origin}/v3/datachip", headers=self.auth(u1), json={
            "name": "test",
            "content": "a" * (500 * 1024 * 1024 + 1)
        })
        assert r.status_code == 413

        # Happy path
        r = requests.post(f"{self.origin}/v3/datachip", headers=self.auth(u1), json={
            "name": "KingOfSlobber",
            "content": "Murphy Skjønsberg"
        })
        assert r.status_code == 200
        dc1 = r.json()
        assert dc1["id"].startswith("dc_")
        assert dc1["name"] == "KingOfSlobber"
        assert dc1["content"] == "Murphy Skjønsberg"
        assert dc1["creator"] == u1.client
        assert dc1["created"] is not None
        assert dc1["updated"] is not None
        assert dc1["deleted"] is None
        self.chips.append((dc1["id"], u1))

        # Create another, belonging to u2
        r = requests.post(f"{self.origin}/v3/datachip", headers=self.auth(u2), json={
            "name": "KingOfMacaroni",
            "content": "Logan Skjønsberg"
        })
        assert r.status_code == 200
        dc2 = r.json()
        assert dc2["id"].startswith("dc_")
        assert dc2["name"] == "KingOfMacaroni"
        assert dc2["content"] == "Logan Skjønsberg"
        assert dc2["creator"] == u2.client
        assert dc2["created"] is not None
        assert dc2["updated"] is not None
        assert dc2["deleted"] is None

        # List them
        r = requests.get(f"{self.origin}/v3/datachips", headers=self.auth(u1))
        assert r.status_code == 200

        # We can't verify individual entities b/c we don't guarantee that we start w/
        # an empty database.
        ids = [dc["id"] for dc in r.json()]
        assert len(ids) >= 2
        for id, _ in self.chips:
            assert id in ids
        assert ids.index(dc1["id"]) > ids.index(dc2["id"])

        # Only return things belonging to u2
        r = requests.get(f"{self.origin}/v3/datachips", params={"creator": u1.client}, headers=self.auth(u1))
        assert r.status_code == 200
        assert len(r.json()) >=  1
        for id, u in self.chips:
            if u == u1:
                assert id in [dc["id"] for dc in r.json()]
            else:
                assert id not in [dc["id"] for dc in r.json()]

        # Make sure u2 can't delete something owned by u1
        r = requests.patch(f"{self.origin}/v3/datachip/{dc1['id']}", headers=self.auth(u2), json={
            "deleted": True
        })
        assert r.status_code == 403

        # Make sure u1 can delete something they own
        r = requests.patch(f"{self.origin}/v3/datachip/{dc1['id']}", headers=self.auth(u1), json={
            "deleted": True
        })
        assert r.status_code == 200
        deleted = r.json()
        for k,v in dc1.items():
            if k != "deleted" and k != "updated":
                assert v == deleted[k]
            assert deleted["deleted"] is not None
            assert datetime.fromisoformat(deleted["updated"]) > datetime.fromisoformat(dc1["updated"])

        # Make sure deleted things aren't listed by default
        r = requests.get(f"{self.origin}/v3/datachips", headers=self.auth(u1))
        assert r.status_code == 200
        assert dc1["id"] not in [dc["id"] for dc in r.json()]

        # ...unless the client asks for them
        r = requests.get(f"{self.origin}/v3/datachips", params={"deleted": True}, headers=self.auth(u1))
        assert r.status_code == 200
        assert dc1["id"] in [dc["id"] for dc in r.json()]

        # Make sure u1 can undelete something they own
        r = requests.patch(f"{self.origin}/v3/datachip/{dc1['id']}", headers=self.auth(u1), json={
            "deleted": False
        })
        assert r.status_code == 200
        undeleted = r.json()
        for k,v in dc1.items():
            if k != "deleted" and k != "updated":
                assert v == deleted[k]
            assert undeleted["deleted"] is None
            assert datetime.fromisoformat(undeleted["updated"]) > datetime.fromisoformat(deleted["updated"])

    def tearDown(self):
        for (id, user) in self.chips:
            r = requests.patch(f"{self.origin}/v3/datachip/{id}", headers=self.auth(user), json={
                "deleted": True
            })
            r.raise_for_status()

