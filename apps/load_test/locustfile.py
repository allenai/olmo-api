import json
import os
import time
from contextlib import suppress
from typing import Any
from uuid import uuid4

import requests
from locust import HttpUser, task

# config
FASTAPI_BASE_URL = os.environ.get("FASTAPI_BASE_URL", "http://localhost:8888")
FLASK_BASE_URL = os.environ.get("FLASK_BASE_URL", "http://localhost:8000")

# Olmo-3.1-32B-Instruct
MODEL = os.environ.get("MODEL", "sleep")
NUM_THREADS_TO_CREATE = int(os.environ.get("NUM_THREADS", "3"))

# Helpers
#
def auth_headers(user_id: str) -> dict[str, str]:
    return {"X-Anonymous-User-ID": user_id}


# both use the same database -- so we can create and delete on either
# only using this because it saves -- v5 is WIP (doesnt save)
def make_thread(*, user_id: str, model: str = MODEL, content: str = "hello") -> str | None:
    # prefer v4 for create
    with requests.post(
        f"{FLASK_BASE_URL}/v4/threads/",
        json={"model": model, "content": content},
        headers=auth_headers(user_id=user_id),
        stream=True,
        timeout=None  # noqa: S113
    ) as resp:
        thread_id: str | None = None
        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                if thread_id is None:
                    thread_id = data.get("message")
            # no break -- we consume the response

    return thread_id



# Abstract classes
#
class BaseUser(HttpUser):
    abstract = True

    thread_ids: list[str]
    user_id: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = str(uuid4())
        self.thread_ids = []

    def create_thread(self, url: str, data: dict[str, Any]):
        raise NotImplementedError

    def measure_create_thread(self, url: str) -> None:
        thread_id: str | None = None
        ttft_ms: float | None = None

        with self.create_thread(url=url, data={"model": MODEL, "content": "hello"}) as resp:
            ttft_start = time.perf_counter()
            for line in resp.iter_lines():
                if line:
                    parsed = json.loads(line)
                    if thread_id is None:
                        thread_id = parsed.get("message")
                    if parsed.get("type") in {"modelResponse", "thinking", "toolCall"}:
                        ttft_ms = (time.perf_counter() - ttft_start) * 1000
                        break

            # consume rest of response
            for _ in resp.iter_lines():
                pass

            resp.success()

        if ttft_ms is not None:
            self.environment.events.request.fire(
                request_type="POST",
                name=f"{url} (TTFT)",
                response_time=ttft_ms,
                response_length=0,
                exception=None,
                context={},
            )

        if thread_id:
            self.thread_ids.append(thread_id)

    def cleanup_threads(self):
        for thread_id in self.thread_ids:
            with suppress(Exception):
                requests.delete(f"{FASTAPI_BASE_URL}/v5/threads/{thread_id}", headers=auth_headers(user_id=self.user_id), timeout=None)  # noqa: S113


class FastAPIUser(BaseUser):
    abstract = True
    host = FASTAPI_BASE_URL

    def create_thread(self, url: str, data: dict[str, Any]):
        return self.client.post(
            url,
            data=data,  # form data
            headers=auth_headers(user_id=self.user_id),
            stream=True,
            catch_response=True,
        )


class FlaskUser(BaseUser):
    abstract = True
    host = FLASK_BASE_URL

    def create_thread(self, url: str, data: dict[str, Any]):
        return self.client.post(
            url,
            json=data,
            headers=auth_headers(user_id=self.user_id),
            stream=True,
            catch_response=True,
        )


# Fake requests
#
class FastAPIFakeRequestUser(FastAPIUser):
    @task
    def fake_request(self) -> None:
        self.client.get("/v5/fake-request")


class FlaskFakeRequestUser(FlaskUser):
    @task
    def fake_request(self) -> None:
        self.client.get("/v4/fake-request")


# Get threads requests
#
class FastAPIGetThreadListUser(FastAPIUser):
    def on_start(self) -> None:
        for _ in range(NUM_THREADS_TO_CREATE):
            thread_id = make_thread(user_id=self.user_id)
            if thread_id:
                self.thread_ids.append(thread_id)

    def on_stop(self) -> None:
        self.cleanup_threads()

    @task
    def get_threads(self) -> None:
        self.client.get("/v5/threads/", headers=auth_headers(user_id=self.user_id))


class FlaskGetThreadListUser(FlaskUser):
    def on_start(self) -> None:
        for _ in range(NUM_THREADS_TO_CREATE):
            thread_id = make_thread(user_id=self.user_id)
            if thread_id:
                self.thread_ids.append(thread_id)

    def on_stop(self) -> None:
        self.cleanup_threads()

    @task
    def get_threads(self) -> None:
        self.client.get("/v4/threads/", headers=auth_headers(user_id=self.user_id))


# Create new threads
#
class FastAPICreateThreadUser(FastAPIUser):
    @task
    def test_create_thread(self) -> None:
        self.measure_create_thread('/v5/threads/chat')

    def on_stop(self) -> None:
        self.cleanup_threads()

class FlaskCreateThreadUser(FlaskUser):
    @task
    def test_create_thread(self) -> None:
        self.measure_create_thread("/v4/threads/")

    def on_stop(self) -> None:
        self.cleanup_threads()
