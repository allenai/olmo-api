from . import base, util

import requests
import json

def all_message_ids(messages: list[dict]) -> list[str]:
    ids = [ m["id"] for m in messages ]
    for m in messages:
        ids += all_message_ids(m["children"]) if m.get("children") is not None else []
    return ids

class TestPrivateMessages(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        # Make sure threaded messages all have the same visibility level
        for (is_parent_private, is_child_private) in [
            (True, False),
            (False, True),
        ]:
            r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
                "content": "I'm a magical labrador named Murphy, who are you? ",
                "private": is_parent_private,
            })
            r.raise_for_status()

            parent_id = json.loads(util.last_response_line(r))["id"]
            response_id = json.loads(util.last_response_line(r))["children"][0]["id"]
            self.messages.append((parent_id, u1))

            r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
                "content": "I am magical though, really.",
                "parent": response_id,
                "private": is_child_private,
            })
            assert r.status_code == 400

        # Make sure non-boolean values return a 400
        for invalid in [ "true", "false", "0", "1", "yes", "no", "maybe", 1, 1.0, 0, 0.0 ]:
            r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
                "content": "I'm a magical labrador named Murphy, who are you? ",
                "private": invalid,
            })
            assert r.status_code == 400

        # Makes sure model responses share the private level of their parent
        r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
            "content": "I'm a magical labrador named Murphy, who are you? ",
            "private": True,
        })
        r.raise_for_status()
        im1 = json.loads(util.last_response_line(r))
        self.messages.append((im1["id"], u1))
        assert im1["private"] == True
        assert im1["children"][0]["private"] == True

        # Make sure child messages transitively inherit the root's private level
        r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u1), json={
            "content": "That's great, do you like eating socks?",
            "parent": im1["children"][0]["id"],
        })
        r.raise_for_status()
        im2 = json.loads(util.last_response_line(r))
        assert im2["private"] == True

        # Verify visibility enforcement of GET /message/:id endpoints
        private_ids = [ im1["id"], im1["children"][0]["id"], im2["id"], im2["children"][0]["id"] ]
        for mid in private_ids:
            # Make sure private messages are not visible to other users
            r = requests.get(f"{self.origin}/v3/message/{mid}", headers=self.auth(u2))
            assert r.status_code == 403

            # ...but are to the users who create them
            r = requests.get(f"{self.origin}/v3/message/{mid}", headers=self.auth(u1))
            assert r.status_code == 200

        # Verify GET /messages doesn't return private messages inappropriately. We sort by recency,
        # so we shouldn't need to paginate (but still set a high limit to be safe).
        for (user, should_see_private) in [ (u2, False), (u1, True) ]:
            expect = 0 if not should_see_private else len(private_ids)

            r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(user), params={ "limit": 100 })
            r.raise_for_status()
            ids = set(all_message_ids(r.json()["messages"]))
            assert len(ids.intersection(private_ids)) == expect

            r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(user), params={
                "limit": 100,
                "creator": u1.client
            })
            r.raise_for_status()
            ids = set(all_message_ids(r.json()["messages"]))
            assert len(ids.intersection(private_ids)) == expect

        # Make sure only the original creator can add messages to an private thread
        for mid in [ im1["children"][0]["id"], im2["children"][0]["id"] ]:
            r = requests.post(f"{self.origin}/v3/message", headers=self.auth(u2), json={
                "content": "dogs are unicorns, or are unicorns dogs?",
                "parent": mid
            })
        assert r.status_code == 403

    def tearDown(self):
        for (id, user) in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()

