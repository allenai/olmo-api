import json
import re
from typing import Any

import pytest
import requests

from e2e import util
from e2e.model_output_testing import test_cases
from src.thread.thread_models import Thread

from . import base


@pytest.mark.production
class TestTextModels(base.IntegrationTest):
    messages: list[tuple[str, base.AuthenticatedClient]] = []
    child_msgs: list[tuple[str, base.AuthenticatedClient]] = []

    def add_messages_in_thread(self, thread: Thread, user: base.AuthenticatedClient):
        for c in thread.messages:
            c_tup = (c.id, user)
            self.messages.append(c_tup)
            self.child_msgs.append(c_tup)

    def runTest(self):
        anonymous_user = self.user(anonymous=True)

        # Iterate through the configured test cases
        # TODO: group test output by host/model
        for model_tests in test_cases.test_cases:
            # TODO: make each test case a separate test in the test output
            for tc in model_tests.tests:
                payload: dict[str, Any] = {
                    "host": (None, model_tests.host),
                    "model": (None, model_tests.model),
                    "content": (None, tc.input),
                }

                for k, v in model_tests.defaults.__dict__.items():
                    if v is not None and k != "stop":
                        payload[k] = (None, str(v))
                    elif k == "stop" and v:
                        payload[k] = (None, json.dumps(v))

                if tc.files:
                    for file in tc.files:
                        image_req = requests.get(file.url, stream=True)
                        name = file.url.split("/")[-1]
                        payload["files"] = (name, image_req.content, file.mime)

                request = requests.post(
                    f"{self.origin}/v4/threads",
                    headers=self.auth(anonymous_user),
                    files=payload,
                )

                request.raise_for_status()
                response_thread = Thread.model_validate_json(util.second_to_last_response_line(request))
                self.add_messages_in_thread(response_thread, anonymous_user)
                lines = list(request.text.splitlines())
                json_lines = [json.loads(line) for line in lines]
                final_thread = json_lines[-2]
                last_message = final_thread["messages"][-1]

                text = last_message["content"]

                # Validate acceptance
                for acc in tc.acceptance:
                    kind = acc.kind
                    expected = acc.expected
                    prefix = f"{model_tests.model}:{tc.id} -"
                    if kind == "exact":
                        assert str(text).strip() == str(expected).strip(), f"{prefix} Expected exact '{expected}', got '{text}'"
                    elif kind == "contains":
                        assert str(expected) in str(text), f"{prefix} Expected '{text}' to contain '{expected}'"
                    elif kind == "regex":
                        assert re.search(str(expected), str(text)), f"{prefix} Regex '{expected}' did not match '{text}'"
                    else:
                        pytest.fail(f"{prefix} Unknown acceptance kind: {kind}")

    def tearDown(self):
        # Since the delete operation cascades, we have to find all child messages
        # and remove them from self.messages. Otherwise, we'll run into 404 errors
        # when executing r.raise_for_status()
        messages_to_delete = [msg for msg in self.messages if msg not in self.child_msgs]

        for id, user in messages_to_delete:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()
