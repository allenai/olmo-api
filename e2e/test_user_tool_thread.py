import json
from typing import Any

import requests

from e2e import util
from src.thread.thread_models import Thread

from . import base

tool_def = '{ "name": "get weather", "description": "get the weather", "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "the city name"} } } }'
tool_def_two = '{ "name": "get weather two", "description": "get the weather again", "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "the city name"} } } }'

tool_def_multi_type = """
    {
    "name": "getStockIndexCloseValue",
    "description": "Get the value of a stock index at close on a particular day",
    "parameters": {
      "type": "object",
      "properties": {
        "stockIndex": {
          "type": "string",
          "enum": [
            "Dow Jones",
            "NASDAQ",
            "S&P 500"
          ]
        },
        "daysAgo": {
          "type": "number"
        },
        "moreData": {
          "type": "object",
          "properties": {
            "foo": {
              "type": "string"
            },
            "bar": {
              "type": "string"
            }
          },
          "required": [
            "bar"
          ],
          "propertyOrdering": [
            "foo",
            "bar"
          ]
        }
      },
      "required": [
        "stockIndex",
        "moreData"
      ],
      "propertyOrdering": [
        "stockIndex",
        "daysAgo",
        "moreData"
      ]
    }
  }
"""

default_model_options = {
    "host": (None, "test_backend"),
    "model": (None, "test-model"),
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
                "tool_definitions": (None, f"[{tool_def}]"),
                **default_model_options,
            },
        )
        create_message_request.raise_for_status()

        lines = list(create_message_request.text.splitlines())

        json_lines = [json.loads(line) for line in lines]

        first_yield = json_lines[0]
        assert first_yield["type"] == "start"

        first_yield = json_lines[1]
        assert first_yield["id"] is not None
        thread_id = first_yield["id"]
        thread_messages = first_yield["messages"]
        self.messages.append((thread_id, anonymous_user))
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

        last_assistant_message = final_messages[-2]
        last_message = final_messages[-1]

        assert last_message["role"] == "tool_call_result"

        assert last_assistant_message["role"] == "assistant"
        assert len(last_assistant_message["toolCalls"]) == 2

        assert len(last_assistant_message["toolDefinitions"]) == 2

        # Find user call
        user_tool_call = next(
            tool for tool in last_assistant_message["toolCalls"] if tool["toolSource"] == "user_defined"
        )

        create_tool_response = requests.post(
            f"{self.origin}/v4/threads/",
            headers=self.auth(anonymous_user),
            files={
                "content": (None, "weather is good"),
                "role": (None, "tool_call_result"),
                "tool_call_id": (None, user_tool_call["toolCallId"]),
                "parent": (None, final_messages[-1]["id"]),
                "tool_definitions": (None, f"[{tool_def}]"),  # current spec is for this to be ignored
                **default_model_options,
            },
        )
        create_tool_response.raise_for_status()

        lines = list(create_tool_response.text.splitlines())

        json_lines = [json.loads(line) for line in lines]

        first_yield = json_lines[0]
        assert first_yield["type"] == "start"

        final_yield = json_lines[-2]

        thread_messages = final_yield["messages"]

        assert len(thread_messages[-1]["toolDefinitions"]) == 2
        assert thread_messages[0]["role"] == "tool_call_result"
        assert thread_messages[1]["role"] == "assistant"

        # load thead and verify content...

        r = requests.get(f"{self.origin}/v4/threads/{thread_id}", headers=self.auth(anonymous_user))
        r.raise_for_status()

        thread = r.json()

        for item in thread["messages"]:
            if item["role"] != "system":
                assert len(item["toolDefinitions"]) == 2

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        messages_to_delete = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in messages_to_delete:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()


class TestUserComplexToolDefThreadEndpoints(base.IntegrationTest):
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
                "tool_definitions": (None, f"[{tool_def_multi_type}]"),
                **default_model_options,
            },
        )
        create_message_request.raise_for_status()
        response_thread = Thread.model_validate_json(util.second_to_last_response_line(create_message_request))
        self.messages.append((response_thread.id, anonymous_user))

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        messages_to_delete = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in messages_to_delete:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()


class TestMultipleUserToolCallsThreadEndpoints(base.IntegrationTest):
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
                "tool_definitions": (None, f"[{tool_def}, {tool_def_two}]"),
                **default_model_options,
            },
        )
        create_message_request.raise_for_status()

        lines = list(create_message_request.text.splitlines())

        json_lines = [json.loads(line) for line in lines]

        first_yield = json_lines[0]
        assert first_yield["type"] == "start"

        first_yield = json_lines[1]
        assert first_yield["id"] is not None

        self.messages.append((first_yield["id"], anonymous_user))
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

        last_assistant_message = final_messages[-2]
        last_message = final_messages[-1]

        assert last_message["role"] == "tool_call_result"

        assert last_assistant_message["role"] == "assistant"
        assert len(last_assistant_message["toolCalls"]) == 3  # two user 1 internal

        # Find user call
        user_tool_calls = list(
            filter(lambda tool: tool["toolSource"] == "user_defined", last_assistant_message["toolCalls"])
        )

        call_1 = user_tool_calls[0]
        call_2 = user_tool_calls[1]
        create_tool_response = requests.post(
            f"{self.origin}/v4/threads/",
            headers=self.auth(anonymous_user),
            files={
                "content": (None, "weather is good"),
                "role": (None, "tool_call_result"),
                "tool_call_id": (None, call_1["toolCallId"]),
                "parent": (None, final_messages[-1]["id"]),
                **default_model_options,
            },
        )
        create_tool_response.raise_for_status()

        lines = list(create_tool_response.text.splitlines())

        json_lines = [json.loads(line) for line in lines]

        first_yield = json_lines[0]
        assert first_yield["type"] == "start"

        final_yield = json_lines[-2]

        thread_messages = final_yield["messages"]
        assert len(thread_messages) == 1

        assert len(thread_messages[-1]["toolDefinitions"]) == 3
        assert thread_messages[0]["role"] == "tool_call_result"

        create_tool_response_2 = requests.post(
            f"{self.origin}/v4/threads/",
            headers=self.auth(anonymous_user),
            files={
                "content": (None, "weather is good"),
                "role": (None, "tool_call_result"),
                "tool_call_id": (None, call_2["toolCallId"]),
                "parent": (None, thread_messages[0]["id"]),
                **default_model_options,
            },
        )

        create_tool_response_2.raise_for_status()

        lines = list(create_tool_response_2.text.splitlines())

        json_lines = [json.loads(line) for line in lines]
        # assert assistant message

        final_yield = json_lines[-2]

        thread_messages = final_yield["messages"]
        assert len(thread_messages) == 2

        assert thread_messages[0]["role"] == "tool_call_result"
        assert thread_messages[1]["role"] == "assistant"

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        messages_to_delete = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in messages_to_delete:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
