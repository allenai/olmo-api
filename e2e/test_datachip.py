from datetime import UTC, datetime

import pytest
import requests

from . import base


class TestDatachipEndpoints(base.IntegrationTest):
    chips: list[tuple[str, base.AuthenticatedClient]] = []

    @pytest.mark.skip(reason="Datachips are deprecated")
    def runTest(self):
        # Deleted datachip refs can't be reused, which means we need to prefix names used in this test.
        prefix = f"{type(self).__name__}_{datetime.now(UTC).strftime('%s')}_"

        # Make sure all endpoints require auth
        for r in [
            requests.post(f"{self.origin}/v3/datachip"),
            requests.get(f"{self.origin}/v3/datachips"),
            requests.patch(f"{self.origin}/v3/datachip/XXX"),
            requests.get(f"{self.origin}/v3/datachip/XXX"),
        ]:
            assert r.status_code == 401

        u1 = self.user("test1@localhost")
        # u2 = self.user("test2@localhost")

        # Must specify a non-empty name
        empty = ["", "   "]
        for name in empty:
            r = requests.post(f"{self.origin}/v3/datachip", headers=self.auth(u1), json={"name": name})
            assert r.status_code == 400

        # Names must only have alphanumeric characters and _ or -. We don't test for everything.
        invalid = ["! dog", "/hi", "hi/there", "$hey!"]
        for name in invalid:
            r = requests.post(
                f"{self.origin}/v3/datachip",
                headers=self.auth(u1),
                json={"name": name, "content": "Murphy"},
            )
            assert r.status_code == 400

        # Must specify content
        for content in empty:
            r = requests.post(
                f"{self.origin}/v3/datachip",
                headers=self.auth(u1),
                json={"name": "test", "content": content},
            )
            assert r.status_code == 400

        # Content must be <= 500MB
        r = requests.post(
            f"{self.origin}/v3/datachip",
            headers=self.auth(u1),
            json={"name": "test", "content": "a" * (500 * 1024 * 1024 + 1)},
        )
        assert r.status_code == 413

        # Happy path
        r = requests.post(
            f"{self.origin}/v3/datachip",
            headers=self.auth(u1),
            json={"name": f"{prefix}KingOfSlobber", "content": "Murphy Skjønsberg"},
        )
        assert r.status_code == 200
        dc1 = r.json()
        assert dc1["id"].startswith("dc_")
        assert dc1["name"] == f"{prefix}KingOfSlobber"
        assert dc1["ref"] == f"{u1.client}/{prefix}KingOfSlobber"
        assert dc1["content"] == "Murphy Skjønsberg"
        assert dc1["creator"] == u1.client
        assert dc1["created"] is not None
        assert dc1["updated"] is not None
        assert dc1["deleted"] is None
        self.chips.append((dc1["id"], u1))

        # No duplicates
        r = requests.post(
            f"{self.origin}/v3/datachip",
            headers=self.auth(u1),
            json={"name": f"{prefix}KingOfSlobber", "content": "Sam Skjønsberg"},
        )
        assert r.status_code == 400
        assert r.json()["error"]["message"] == f'datachip "{u1.client}/{prefix}KingOfSlobber" already exists'

        # Get the chip
        r = requests.get(f"{self.origin}/v3/datachip/{dc1['id']}", headers=self.auth(u1))
        assert r.status_code == 200
        for k, v in dc1.items():
            assert v == r.json()[k]

        # List them
        r = requests.get(f"{self.origin}/v3/datachips", headers=self.auth(u1))
        assert r.status_code == 200

        # We can't verify individual entities b/c we don't guarantee that we start w/
        # an empty database.
        dclist1 = r.json()
        ids = [dc["id"] for dc in dclist1["datachips"]]
        assert len(ids) >= 2
        for id, _ in self.chips:
            assert id in ids
        assert dclist1["meta"]["limit"] == 10
        assert dclist1["meta"]["offset"] == 0

        # Verify pagination
        r = requests.get(f"{self.origin}/v3/datachips", params={"limit": 1}, headers=self.auth(u1))
        assert r.status_code == 200
        dclist2 = r.json()
        assert len(dclist2["datachips"]) == 1
        assert dclist1["datachips"][0] == dclist2["datachips"][0]
        assert dclist2["meta"]["limit"] == 1
        assert dclist2["meta"]["offset"] == 0

        r = requests.get(
            f"{self.origin}/v3/datachips",
            params={"limit": 1, "offset": 1},
            headers=self.auth(u1),
        )
        assert r.status_code == 200
        dclist3 = r.json()
        assert len(dclist3["datachips"]) == 1
        assert dclist1["datachips"][1] == dclist3["datachips"][0]
        assert dclist3["meta"]["limit"] == 1
        assert dclist3["meta"]["offset"] == 1

        # Verify handling of invalid pagination
        for o, l in [
            ("-1", "0"),
            ("0", "-1"),
            ("1.5", "0"),
            ("0", "1.5"),
            ("0", "101"),
        ]:
            r = requests.get(
                f"{self.origin}/v3/datachips",
                params={"offset": o, "limit": l},
                headers=self.auth(u1),
            )
            assert r.status_code == 400

        # # Only return things belonging to u2
        # r = requests.get(
        #     f"{self.origin}/v3/datachips",
        #     params={"creator": u1.client},
        #     headers=self.auth(u1),
        # )
        # assert r.status_code == 200
        # dclist = r.json()
        # assert len(dclist["datachips"]) >= 1
        # for id, u in self.chips:
        #     if u == u1:
        #         assert id in [dc["id"] for dc in dclist["datachips"]]
        #     else:
        #         assert id not in [dc["id"] for dc in dclist["datachips"]]

        # # Make sure u2 can't delete something owned by u1
        # r = requests.patch(
        #     f"{self.origin}/v3/datachip/{dc1['id']}",
        #     headers=self.auth(u2),
        #     json={"deleted": True},
        # )
        # assert r.status_code == 403

        # Make sure u1 can delete something they own
        r = requests.patch(
            f"{self.origin}/v3/datachip/{dc1['id']}",
            headers=self.auth(u1),
            json={"deleted": True},
        )
        assert r.status_code == 200
        deleted = r.json()
        for k, v in dc1.items():
            if k not in {"deleted", "updated"}:
                assert v == deleted[k]
            assert deleted["deleted"] is not None
            assert datetime.fromisoformat(deleted["updated"]) > datetime.fromisoformat(dc1["updated"])

        # Deleted refs still can't be reused
        r = requests.post(
            f"{self.origin}/v3/datachip",
            headers=self.auth(u1),
            json={"name": dc1["name"], "content": "Sam Skjønsberg"},
        )
        assert r.status_code == 400
        assert r.json()["error"]["message"] == f"datachip \"{dc1['ref']}\" already exists"

        # Make sure deleted things aren't listed by default
        r = requests.get(f"{self.origin}/v3/datachips", headers=self.auth(u1))
        assert r.status_code == 200
        assert dc1["id"] not in [dc["id"] for dc in r.json()["datachips"]]

        # ...unless the client asks for them
        r = requests.get(
            f"{self.origin}/v3/datachips",
            params={"deleted": True},
            headers=self.auth(u1),
        )
        assert r.status_code == 200
        assert dc1["id"] in [dc["id"] for dc in r.json()["datachips"]]

        # Make sure u1 can undelete something they own
        r = requests.patch(
            f"{self.origin}/v3/datachip/{dc1['id']}",
            headers=self.auth(u1),
            json={"deleted": False},
        )
        assert r.status_code == 200
        undeleted = r.json()
        for k, v in dc1.items():
            if k not in {"deleted", "updated"}:
                assert v == deleted[k]
            assert undeleted["deleted"] is None
            assert datetime.fromisoformat(undeleted["updated"]) > datetime.fromisoformat(deleted["updated"])

    def tearDown(self):
        for id, user in self.chips:
            r = requests.patch(
                f"{self.origin}/v3/datachip/{id}",
                headers=self.auth(user),
                json={"deleted": True},
            )
            r.raise_for_status()
