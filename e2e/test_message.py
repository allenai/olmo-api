import json
from datetime import UTC, datetime

import pytest
import requests

from e2e import util

from . import base

default_model_options = {
    "host": (None, "modal"),
    "model": (None, "OLMoE-1B-7B-0924-Instruct"),
}


default_options = [
    ("max_tokens", 2048),
    ("temperature", 0.7),
    ("n", 1),
    ("top_p", 1.0),
    ("logprobs", None),
    ("stop", None),
]


class TestAnonymousMessageEndpoints(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []
    child_msgs: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        anonymous_user = self.user(anonymous=True)

        create_message_request = requests.post(
            f"{self.origin}/v4/message/stream",
            headers=self.auth(anonymous_user),
            json={
                "content": "I'm a magical labrador named Murphy, who are you? ",
                "private": True,
                **default_model_options,
            },
            files={
                "content": (None, "I'm a magical labrador named Murphy, who are you?"),
                "private": (None, str(True)),
                **default_model_options,
            },
        )
        create_message_request.raise_for_status()

        response_messages = [json.loads(util.last_response_line(create_message_request))]
        first_message = response_messages[0]
        self.messages.append((first_message["id"], anonymous_user))

        for child in first_message["children"]:
            child_and_user = (child["id"], anonymous_user)
            self.messages.append(child_and_user)
            self.child_msgs.append(child_and_user)

        assert first_message["private"] is True
        assert first_message["expiration_time"] is not None

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        messages_to_delete = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in messages_to_delete:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()


class TestMessageEndpoints(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []
    child_msgs: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        # Make sure all endpoints fail w/o auth
        for r in [
            requests.get(f"{self.origin}/v3/messages"),
            requests.post(
                f"{self.origin}/v4/message/stream",
                # The Pydantic validation setup  makes it so that we run request validation before auth validation
                files={
                    "content": (None, "I'm a magical labrador named Murphy, who are you?"),
                    "private": (None, str(True)),
                    **default_model_options,
                },
            ),
            requests.get(f"{self.origin}/v3/message/XXX"),
            requests.delete(f"{self.origin}/v3/message/XXX"),
        ]:
            assert r.status_code == 401

        u1 = self.user("test1@localhost")
        u2 = self.user("test2@localhost")

        # Create a message belonging to u1
        r = requests.post(
            f"{self.origin}/v4/message/stream",
            headers=self.auth(u1),
            files={
                "content": (None, "I'm a magical labrador named Murphy, who are you?"),
                **default_model_options,
            },
        )
        r.raise_for_status()

        msgs = [json.loads(util.last_response_line(r))]
        m1 = msgs[0]
        self.messages.append((m1["id"], u1))
        for c in m1["children"]:
            c_tup = (c["id"], u1)
            self.messages.append(c_tup)
            self.child_msgs.append(c_tup)

        for name, value in default_options:
            assert m1["opts"][name] == value
        assert m1["model_id"] == default_model_options["model"]
        assert m1["model_host"] == default_model_options["host"]

        # Verify GET /v3/message/:id
        r = requests.get(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        msgs.append(r.json())
        for m in msgs:
            assert m["id"] is not None
            assert m["content"] == "I'm a magical labrador named Murphy, who are you? "
            assert m["creator"] == u1.client
            assert m["role"] == "user"
            assert m["model_type"] is None  # We only set model_type for assistant messages
            assert datetime.fromisoformat(m["created"]) <= datetime.now(UTC)
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
        r = requests.post(
            f"{self.origin}/v4/message/stream",
            headers=self.auth(u1),
            files={
                "content": (None, "Complete this thought: I like "),
                "parent": (None, c1["id"]),
                **default_model_options,
            },
        )
        r.raise_for_status()
        c2 = json.loads(util.last_response_line(r))
        c_tup = (c2["id"], u1)
        self.messages.append(c_tup)
        self.child_msgs.append(c_tup)
        for c in c2["children"]:
            c_tup = (c["id"], u1)
            self.messages.append(c_tup)
            self.child_msgs.append(c_tup)
        assert c2["parent"] == c1["id"]
        assert c2["content"] == "Complete this thought: I like "
        assert len(c2["children"]) == 1

        # Verify the full tree
        r = requests.get(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        expect = [
            (m1["id"], "user", None, 1),
            (c1["id"], "assistant", "chat", 1),
            (c2["id"], "user", None, 1),
            (c2["children"][0]["id"], "assistant", "chat", 0),
        ]
        actual = []
        node = r.json()
        while node is not None:
            actual.append((
                node["id"],
                node["role"],
                node["model_type"],
                len(node["children"]) if node["children"] else 0,
            ))
            node = node["children"][0] if node["children"] else None
        assert actual == expect

        # Create a message belonging to u2
        r = requests.post(
            f"{self.origin}/v4/message/stream",
            headers=self.auth(u2),
            files={
                "content": (None, "I'm a wizardly horse named Grasshopper, who are you? "),
                **default_model_options,
            },
        )
        r.raise_for_status()
        m2 = json.loads(util.last_response_line(r))
        self.messages.append((m2["id"], u2))
        for c in m2["children"]:
            c_tup = (c["id"], u2)
            self.messages.append(c_tup)
            self.child_msgs.append(c_tup)

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
        # assert ids.index(m2["id"]) < ids.index(m1["id"])
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
        assert m1["id"] in offset_ids

        r = requests.get(f"{self.origin}/v3/messages?offset=1&limit=1", headers=self.auth(u1))
        r.raise_for_status()
        limit_msglist = r.json()
        assert limit_msglist["meta"]["total"] > 0
        assert limit_msglist["meta"]["offset"] == 1
        assert limit_msglist["meta"]["limit"] == 1
        assert len(limit_msglist["messages"]) == 1
        assert limit_msglist["messages"][0]["id"] == offset_msglist["messages"][0]["id"]

        # List by author
        r = requests.get(
            f"{self.origin}/v3/messages",
            headers=self.auth(u1),
            params={"creator": u1.client},
        )
        r.raise_for_status()
        u1_msglist = r.json()
        assert u1_msglist["meta"]["total"] > 0
        assert u1_msglist["meta"]["total"] < msglist["meta"]["total"]
        ids = [m["id"] for m in u1_msglist["messages"]]
        assert m1["id"] in ids
        # We don't have a a way of setting a second author with the current auth setup. we can probably log in with other users in the future
        # assert m2["id"] not in ids

        # r = requests.get(
        #     f"{self.origin}/v3/messages",
        #     headers=self.auth(u1),
        #     params={"creator": u2.client},
        # )
        # r.raise_for_status()
        # u2_msglist = r.json()
        # assert u2_msglist["meta"]["total"] > 0
        # assert u2_msglist["meta"]["total"] < msglist["meta"]["total"]
        # ids = [m["id"] for m in u2_msglist["messages"]]
        # assert m1["id"] not in ids
        # assert m2["id"] in ids

        # # Make sure u2 can't delete u1
        # r = requests.delete(
        #     f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u2)
        # )
        # assert r.status_code == 403

        # Delete message m1
        r = requests.delete(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        r.raise_for_status()
        assert r.status_code == 200
        self.messages = list(filter(lambda m: m[0] != m1["id"], self.messages))

        # The DB should not have the deleted message anymore
        r = requests.get(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        assert r.status_code == 404

        # Deleting message m1 again should also get a 404
        r = requests.delete(f"{self.origin}/v3/message/{m1['id']}", headers=self.auth(u1))
        assert r.status_code == 404

        # If a deleted parent message has children, those children should be deleted as well
        for c in m1["children"]:
            r = requests.get(f"{self.origin}/v3/message/{c['id']}", headers=self.auth(u1))
            assert r.status_code == 404

        # Don't list deleted messages by default
        r = requests.get(f"{self.origin}/v3/messages", headers=self.auth(u1))
        r.raise_for_status()
        msglist = r.json()
        ids = [m["id"] for m in msglist["messages"]]
        assert m1["id"] not in ids

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
            ),
        ]
        for content, snippet in cases:
            r = requests.post(
                f"{self.origin}/v4/message/stream",
                headers=self.auth(u1),
                files={"content": (None, content), **default_model_options},
            )
            r.raise_for_status()
            m = json.loads(util.last_response_line(r))
            self.messages.append((m["id"], u1))
            assert m["snippet"] == snippet

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        self.messages = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()


class TestMessageValidation(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        # Test inference option validation. Each tuple is of the form:
        # (field_name, invalid_values, valid_values). For these tests we create
        # private messages belonging to u3, as to not pollute data that tests below this
        # use.
        u3 = self.user("test3@localhost")
        fields = [
            # We don't test values numbers close to most maximums b/c they surpass the thresholds
            # of what our tiny local models can do...
            ("max_tokens", [0, 1.0, "three", 4097], [1, 32]),
            ("temperature", [-1.0, "three", 2.1], [0, 0.5, 1]),
            ("top_p", [-1, "three", 1.1], [0.1, 0.5, 1]),
            # TODO: test these cases, once supported (they were disabled when streaming was added)
            ("n", [-1, 1.0, "three", 51], []),
            ("logprobs", [-1, 1.0, "three", 11], [0, 1, 10]),
        ]
        for name, invalid, valid in fields:
            for v in invalid:
                r = requests.post(
                    f"{self.origin}/v4/message/stream",
                    headers=self.auth(u3),
                    files={
                        "content": (None, f'Testing invalid value "{v}" for {name}'),
                        name: (None, v),
                        **default_model_options,
                    },
                )
                assert r.status_code == 400, f"Expected 400 for invalid value {v} for {name}"
            for v in valid:
                # top_p can only be set to a value that isn't 1.0 if temperature is > 0
                opts = {name: (None, v)}
                if name == "top_p" and v != 1.0:
                    opts["temperature"] = (None, 0.5)

                r = requests.post(
                    f"{self.origin}/v4/message/stream",
                    headers=self.auth(u3),
                    files={
                        "content": f'Testing valid value "{v}" for {name}',
                        "private": str(True),
                        **opts,
                        **default_model_options,
                    },
                )
                assert r.status_code == 200, f"Expected 200 for valid value {v} for {name}"
                msg = json.loads(util.last_response_line(r))
                self.messages.append((msg["id"], u3))
                for default_name, default_value in default_options:
                    actual = msg["opts"][default_name]
                    expected = opts.get(default_name, default_value)
                    if actual != expected:
                        msg = f"Value for {default_name} was {actual}, expected {expected}"
                        raise AssertionError(msg)

    def tearDown(self):
        for id, user in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()


class TestLogProbs(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []

    @pytest.mark.skip(reason="We don't have an available model with logprobs")
    def runTest(self):
        u1 = self.user("test1@localhost")

        # Create a message w/ logprobs
        r = requests.post(
            f"{self.origin}/v4/message/stream",
            headers=self.auth(u1),
            files={
                # Together doesn't support Tulu right now. If you want to test logprobs using InferD, change the model sent here to "tulu2"
                # Only "tulu2" supports logprobs currently https://github.com/allenai/inferd-olmo/issues/1
                "model": (None, "tulu2"),
                "content": (None, "why are labradors smarter than unicorns?"),
                "logprobs": (None, str(2)),
                **default_model_options,
            },
        )
        r.raise_for_status()
        lines = list(r.text.splitlines())
        for line in lines[1:-1]:
            chunk = json.loads(line)
            # TODO: I can't explain why, but sometimes there appears to be > 2 in the response.
            # I believe it has to do with this:
            # https://github.com/vllm-project/vllm/blob/6ccc0bfffbcf1b7e927cc3dcf4159fc74ff94d40/vllm/sampling_params.py#L79-L81
            # But I don't follow the reasoning.
            # Requests coming from tulu2 on inferd will have 2 logprobs
            assert all(len(lp) >= 1 for lp in chunk.get("logprobs", []))
        final = json.loads(lines[-1])
        self.messages.append((final["id"], u1))
        assistant_logprobs = final["children"][0].get("logprobs", [])
        assert all(len(lp) >= 1 for lp in assistant_logprobs)
        lp1, lp2 = assistant_logprobs[0][0], assistant_logprobs[0][1]
        lp1 = assistant_logprobs[0][0]
        assert isinstance(lp1.get("text"), str)
        assert isinstance(lp1.get("token_id"), int)
        assert lp1.get("token_id") >= 0
        assert isinstance(lp1.get("logprob"), float)
        assert lp1.get("logprob") > lp2.get("logprob")

    def tearDown(self):
        for id, user in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
