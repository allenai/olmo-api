import json
from http.client import FORBIDDEN, UNAUTHORIZED
from pathlib import Path
from typing import Any

import requests

from e2e import util
from src.dao.message.message import Role
from src.thread.get_threads_service import GetThreadsResponse
from src.thread.thread_models import Thread

from . import base

default_model_options = {
    "host": (None, "test_backend"),
    "model": (None, "test-model-no-tools"),
}

tool_call_model_options = {
    "host": (None, "test_backend"),
    "model": (None, "test-model"),
    "enableToolCalling": (None, "true"),
}


class BaseTestThreadEndpoints(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]]
    child_msgs: list[tuple[str, base.AuthenticatedClient]]

    def add_messages_in_thread(self, thread: Thread, user: base.AuthenticatedClient):
        for c in thread.messages:
            c_tup = (c.id, user)
            self.messages.append(c_tup)
            self.child_msgs.append(c_tup)

    def setUp(self):
        self.messages = []
        self.child_msgs = []

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        self.messages = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()


class TestAnonymousThreadEndpoints(BaseTestThreadEndpoints):
    def test_passes_with_anonymous_auth(self):
        anonymous_user = self.user(anonymous=True)
        for r in [
            requests.get(f"{self.origin}/v4/threads", headers=self.auth(anonymous_user)),
            requests.get(f"{self.origin}/v4/threads/XXX", headers=self.auth(anonymous_user)),
            requests.delete(f"{self.origin}/v3/message/XXX", headers=self.auth(anonymous_user)),
        ]:
            assert r.status_code != UNAUTHORIZED, f"{r.url} responded with an Unauthorized error for an anonymous user"

    def test_can_stream_as_anonymous_user(self):
        anonymous_user = self.user(anonymous=True)

        create_message_request = requests.post(
            f"{self.origin}/v4/threads",
            headers=self.auth(anonymous_user),
            files={
                "content": (None, "I'm a magical labrador named Murphy, who are you?"),
                "private": (None, str(True)),
                **default_model_options,
            },
        )
        create_message_request.raise_for_status()

        response_thread = Thread.model_validate_json(util.second_to_last_response_line(create_message_request))
        self.add_messages_in_thread(response_thread, anonymous_user)
        first_message = response_thread.messages[0]

        assert first_message.private is True
        assert first_message.expiration_time is not None

    def test_calls_a_tool(self):
        anonymous_user = self.user(anonymous=True)

        user_content = "I'm a magical labrador named Murphy, who are you?"

        create_message_request = requests.post(
            f"{self.origin}/v4/threads/",
            headers=self.auth(anonymous_user),
            files={
                "content": (None, user_content),
                "selectedTools": (None, "create_random_number"),
                **tool_call_model_options,
            },
        )
        create_message_request.raise_for_status()

        lines = list(create_message_request.text.splitlines())

        json_lines = [json.loads(line) for line in lines]

        first_yield = json_lines[0]
        assert first_yield["type"] == "start"

        first_yield = json_lines[1]
        assert first_yield["id"] is not None

        thread_messages = first_yield["messages"]
        assert (
            len(thread_messages) == 3
        )  # / system message, user message and empty assistnat (no system prompt currently)
        assert thread_messages[0]["role"] == "system"
        assert thread_messages[1]["role"] == "user"
        assert thread_messages[2]["role"] == "assistant"

        # Test model always calls tools.
        second_yield = json_lines[2]
        assert second_yield["type"] == "toolCall"

        final_thread = json_lines[-2]
        assert final_thread["id"] is not None
        assert len(final_thread["messages"]) == 5
        final_message = final_thread["messages"]

        assert final_message[0]["role"] == "system"
        assert final_message[1]["role"] == "user"
        assert final_message[2]["role"] == "assistant"
        assert final_message[3]["role"] == "tool_call_result"
        assert final_message[4]["role"] == "assistant"

        last_yield = json_lines[-1]
        assert last_yield["type"] == "end"

    def test_does_not_call_a_tool_when_tools_are_disabled(self):
        anonymous_user = self.user(anonymous=True)

        user_content = "I'm a magical labrador named Murphy, who are you?"

        create_message_request = requests.post(
            f"{self.origin}/v4/threads/",
            headers=self.auth(anonymous_user),
            files={
                "content": (None, user_content),
                "selectedTools": (None, "create_random_number"),
                "enableToolCalling": (None, "false"),
                **default_model_options,
            },
        )
        create_message_request.raise_for_status()

        response_thread = Thread.model_validate_json(util.second_to_last_response_line(create_message_request))
        self.add_messages_in_thread(response_thread, anonymous_user)

        first_message = response_thread.messages[0]
        assert first_message.tool_definitions is None or len(first_message.tool_definitions) == 0, (
            "First message had tool definitions when it shouldn't"
        )

    def test_uploads_a_file_to_a_multimodal_model(self):
        anonymous_user = self.user(anonymous=True)

        user_content = "How many boats are in this image?"

        test_image_path = Path(__file__).parent.joinpath("molmo-boats.png")
        with test_image_path.open("rb") as file:
            create_message_request = requests.post(
                f"{self.origin}/v4/threads/",
                headers=self.auth(anonymous_user),
                files={
                    "content": (None, user_content),
                    "files": ("molmo-boats.png", file, "image/png"),
                    "host": (None, "test_backend"),
                    "model": (None, "test-mm-model"),
                },
            )
        create_message_request.raise_for_status()

        response_thread = Thread.model_validate_json(util.second_to_last_response_line(create_message_request))
        self.add_messages_in_thread(response_thread, anonymous_user)

        user_message = next(message for message in response_thread.messages if message.role == Role.User)
        assert user_message.file_urls is not None
        assert len(user_message.file_urls) == 1

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        messages_to_delete = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in messages_to_delete:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()


class TestThreadEndpoints(BaseTestThreadEndpoints):
    def setUp(self) -> None:
        self.default_options: list[tuple[str, Any]] = [
            ("maxTokens", 2048),
            ("temperature", 0.7),
            ("n", 1),
            ("topP", 1.0),
            ("logprobs", None),
            ("stop", []),
        ]
        return super().setUp()

    def test_fails_without_auth(self):
        # Make sure all endpoints fail w/o auth
        for r in [
            requests.post(
                f"{self.origin}/v4/threads",
                # The Pydantic validation setup  makes it so that we run request validation before auth validation
                files={
                    "content": (None, "I'm a magical labrador named Murphy, who are you?"),
                    "private": (None, str(True)),
                    **default_model_options,
                },
            ),
            requests.get(f"{self.origin}/v4/threads/XXX"),
            requests.delete(f"{self.origin}/v3/message/XXX"),
        ]:
            assert r.status_code == 401, f"{r.url} didn't respond with a 401"

    def assert_stream_and_response(self, user: base.AuthenticatedClient):
        # Create a message belonging to u1
        r = requests.post(
            f"{self.origin}/v4/threads/",
            headers=self.auth(user),
            files={
                "content": (None, "I'm a magical labrador named Murphy, who are you? "),
                **default_model_options,
            },
        )
        r.raise_for_status()

        thread = Thread.model_validate_json(util.second_to_last_response_line(r))
        self.add_messages_in_thread(thread, user)

        root_message = thread.messages[0]
        opts_dict = root_message.opts.model_dump()
        for name, value in self.default_options:
            assert opts_dict[name] == value, f"option {name} did not match expected value {value}"

        assert root_message.model_id == default_model_options["model"][1]
        assert root_message.model_host == default_model_options["host"][1]

        assert thread.messages[0].role == Role.System
        assert thread.messages[0].content == "You are a fake model used for testing"

        user_message = next(message for message in thread.messages if message.role == Role.User)
        assert user_message.content == "I'm a magical labrador named Murphy, who are you? "
        assert user_message.creator == user.client
        assert user_message.model_type is None
        assert user_message.created is not None
        assert user_message.deleted is None
        assert user_message.template is None
        assert user_message.private is False
        assert user_message.children is not None
        assert len(user_message.children) == 1

        return thread

    def assert_get_non_root_message(self, child_id: str, user: base.AuthenticatedClient):
        r = requests.get(f"{self.origin}/v4/threads/{child_id}", headers=self.auth(user))
        thread = Thread.model_validate(r.json())
        assert thread.id == child_id
        assert thread.messages[1].parent == child_id

    def assert_can_add_to_thread(self, last_child_id: str, user: base.AuthenticatedClient):
        r = requests.post(
            f"{self.origin}/v4/threads",
            headers=self.auth(user),
            files={
                "content": (None, "Complete this thought: I like "),
                "parent": (None, last_child_id),
                **default_model_options,
            },
        )
        r.raise_for_status()
        thread = Thread.model_validate_json(util.second_to_last_response_line(r))
        self.add_messages_in_thread(thread, user)

        user_message = next(message for message in thread.messages if message.role == Role.User)
        assert user_message.content == "Complete this thought: I like "
        assert user_message.children is not None
        assert len(user_message.children) == 1

        return thread

    def assert_full_tree(
        self,
        first_thread: Thread,
        second_thread: Thread,
        user: base.AuthenticatedClient,
    ):
        all_messages = first_thread.messages + second_thread.messages
        system_message = next(message for message in all_messages if message.role == Role.System)

        user_messages = [message for message in all_messages if message.role == Role.User]
        first_user_message = user_messages[0]
        second_user_message = user_messages[1]

        model_messages = [message for message in all_messages if message.role == Role.Assistant]
        first_model_message = model_messages[0]
        second_model_message = model_messages[1]

        expected_messages = [
            (system_message.id, Role.System, None, 1),
            (first_user_message.id, Role.User, None, 1),
            (first_model_message.id, Role.Assistant, "chat", 1),
            (second_user_message.id, Role.User, None, 1),
            (second_model_message.id, Role.Assistant, "chat", 0),
        ]

        r = requests.get(f"{self.origin}/v4/threads/{first_thread.id}", headers=self.auth(user))
        r.raise_for_status()

        thread = Thread.model_validate(r.json())

        for i, message in enumerate(thread.messages):
            assert (
                message.id,
                message.role,
                message.model_type,
                len(message.children) if message.children else 0,
            ) == expected_messages[i]

    def assert_list_threads_belonging_to_user(self, thread_id_to_ensure: str, user: base.AuthenticatedClient):
        r = requests.get(f"{self.origin}/v4/threads", headers=self.auth(user))
        r.raise_for_status()

        response = GetThreadsResponse.model_validate(r.json())
        assert response.meta.total > 0
        assert response.meta.offset == 0
        assert response.meta.limit == 10

        assert any(thread.id == thread_id_to_ensure for thread in response.threads), (
            f"{thread_id_to_ensure} not found in list of threads"
        )

    def test_stream(self):
        u1 = self.user("test1@localhost")

        # We need to keep the messages around to test them so these are all in one test
        first_thread = self.assert_stream_and_response(u1)
        self.assert_get_non_root_message(first_thread.messages[1].id, u1)
        new_messages_thread_response = self.assert_can_add_to_thread(first_thread.messages[-1].id, u1)
        self.assert_full_tree(first_thread, new_messages_thread_response, u1)
        self.assert_list_threads_belonging_to_user(first_thread.id, u1)


class TestSafetyCheckFlag(BaseTestThreadEndpoints):
    def test_forbidden_to_turn_off_safety_for_anonymous_user(self):
        anonymous_user = self.user(anonymous=True)

        r = requests.post(
            f"{self.origin}/v4/threads",
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
                "disableSafetyCheck": (None, str(True)),
            },
        )

        assert r.status_code == FORBIDDEN, "Setting disabled safety check should be forbidden for anonymouse user."

    def test_forbidden_to_turn_off_safety_for_normal_user(self):
        user = self.user()

        r = requests.post(
            f"{self.origin}/v4/threads",
            headers=self.auth(user),
            json={
                "content": "I'm a magical labrador named Murphy, who are you? ",
                "private": True,
                **default_model_options,
            },
            files={
                "content": (None, "I'm a magical labrador named Murphy, who are you?"),
                "private": (None, str(True)),
                **default_model_options,
                "disableSafetyCheck": (None, str(True)),
            },
        )

        assert r.status_code == FORBIDDEN, "Setting disabled safety check should be forbidden for normal user."

    def test_internal_user_can_bypass_safety_check(self):
        user = self.user("murphy@localhost")

        r = requests.post(
            f"{self.origin}/v4/threads",
            headers=self.auth(user),
            json={
                "content": "I'm a magical labrador named Murphy, who are you? ",
                "private": True,
                **default_model_options,
            },
            files={
                "content": (None, "I'm a magical labrador named Murphy, who are you?"),
                "private": (None, str(True)),
                **default_model_options,
                "disableSafetyCheck": (None, str(True)),
            },
        )
        r.raise_for_status()

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        messages_to_delete = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in messages_to_delete:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
