import json
from typing import Any

import requests

from . import base

default_model_options = {
    "host": (None, "test_backend"),
    "model": (None, "test-model"),
    "files": (None, None),
}


default_options: list[tuple[str, Any]] = [
    ("max_tokens", 2048),
    ("temperature", 0.7),
    ("n", 1),
    ("top_p", 1.0),
    ("logprobs", None),
    ("stop", []),
]


class TestUserToolThreadEndpoints(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []
    child_msgs: list[tuple[str, base.AuthenticatedClient]] = []

    def runTest(self):
        anonymous_user = self.user(anonymous=True)

        user_content = "I'm a magical labrador named Murphy, who are you?"

        create_message_request = requests.post(
            f"{self.origin}/v4/threads/",
            headers=self.auth(anonymous_user),
            files={
                "content": (None, user_content),
                **default_model_options,
                "tool_definitions": '[{ name: "test", description: "yolo" }]',
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

        last_yield = json_lines[-1]

        assert last_yield["type"] == "end"

        final_thread = json_lines[-2]

        assert final_thread["messages"] is not None

        final_messages = final_thread["messages"]

        last_message = final_messages[-1]

        # todo assert last message has tool defintion

        assert last_message["role"] == "assistant"
        for message in final_messages:
            print(message)

        tool_calls = last_message["toolCalls"]

        assert len(tool_calls) == 2

        # find tool call of typer user
        # find tool call of type system

        # call api with response

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        messages_to_delete = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in messages_to_delete:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
