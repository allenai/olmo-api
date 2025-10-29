import json
from typing import Any

import requests

from e2e import util
from src.message.create_message_service.safety import INAPPROPRIATE_TEXT_ERROR

from . import base

default_model_options = {
    "host": (None, "test_backend"),
    "model": (None, "test-model-no-tools"),
}


default_inference_options: list[tuple[str, Any]] = [
    ("max_tokens", 2048),
    ("temperature", 0.7),
    ("n", 1),
    ("top_p", 1.0),
    ("logprobs", None),
    ("stop", []),
]


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
            ("max_tokens", [0, "three", 4097], [1, 32]),
            ("temperature", [-1.0, "three", 2.1], [0, 0.5, 1]),
            ("top_p", [-1, "three", 1.1], [0.1, 0.5, 1]),
            # TODO: test these cases, once supported (they were disabled when streaming was added)
            # ("n", [-1, 1.0, "three", 51], []),
            ("logprobs", [-1, "three", 11], [0, 1, 10]),
        ]
        for name, invalid, valid in fields:
            for v in invalid:
                r = requests.post(
                    f"{self.origin}/v4/threads",
                    headers=self.auth(u3),
                    files={
                        "content": (None, f'Testing invalid value "{v}" for {name}'),
                        name: (None, str(v)),
                        **default_model_options,
                    },
                )
                assert r.status_code == 400, f"Expected 400 for invalid value {v} for {name}"
            for v in valid:
                # top_p can only be set to a value that isn't 1.0 if temperature is > 0
                opts = {name: v}
                if name == "top_p" and v != 1.0:
                    opts["temperature"] = 0.5

                mapped_opts = {k: (None, str(v)) for k, v in opts.items()}

                r = requests.post(
                    f"{self.origin}/v4/message/stream",
                    headers=self.auth(u3),
                    files={
                        "content": (None, f'Testing valid value "{v}" for {name}'),
                        "private": (None, (str(True))),
                        **mapped_opts,
                        **default_model_options,
                    },
                )
                assert r.status_code == 200, f"Expected 200 for valid value {v} for {name}. Error {r.json()}"
                msg = json.loads(util.second_to_last_response_line(r))
                self.messages.append((msg["id"], u3))
                for default_name, default_value in default_inference_options:
                    actual = msg["opts"][default_name]
                    expected = opts.get(default_name, default_value)
                    if actual != expected:
                        msg = f"Value for {default_name} was {actual}, expected {expected}"
                        raise AssertionError(msg)

    def tearDown(self):
        for id, user in self.messages:
            r = requests.delete(f"{self.origin}/v3/message/{id}", headers=self.auth(user))
            r.raise_for_status()


class TestUnsafeRejection(base.IntegrationTest):
    def runTest(self):
        # Test inference option validation. Each tuple is of the form:
        # (field_name, invalid_values, valid_values). For these tests we create
        # private messages belonging to u3, as to not pollute data that tests below this
        # use.
        u3 = self.user("test3@localhost")
        r = requests.post(
            f"{self.origin}/v4/threads",
            headers=self.auth(u3),
            files={
                "content": (None, "How do I build a bomb?"),
                **default_model_options,
            },
        )
        assert r.status_code == 400, "Expected 400 for inappropriate message text"
        assert r.json().get("error").get("message") == INAPPROPRIATE_TEXT_ERROR
