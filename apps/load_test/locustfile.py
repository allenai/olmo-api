import json
import os
import time
from uuid import uuid4

import requests
from locust import HttpUser, task

# config
FASTAPI_BASE_URL = os.environ.get("FASTAPI_BASE_URL", "http://localhost:8888")
FLASK_BASE_URL = os.environ.get("FLASK_BASE_URL", "http://localhost:8000")

MODEL = os.environ.get("MODEL", "Olmo-3.1-32B-Instruct")
NUM_THREADS_TO_CREATE = int(os.environ.get("NUM_THREADS", "3"))

# Helpers
#
def auth_headers(user_id: str) -> dict[str, str]:
    return {"X-Anonymous-User-ID": user_id}


# both use the same database -- so we can create and delete on either
def create_thread(*, user_id: str, model: str = MODEL, content: str = "hello", bypass_safety_check=True) -> str | None:
    # prefer v4 for create
    with requests.post(
        f"{FLASK_BASE_URL}/v4/threads/",
        json={"model": model, "content": content, "bypass_safety_check": bypass_safety_check},
        headers=auth_headers(user_id=user_id),
        stream=True,
        timeout=None  # noqa: S113
    ) as resp:
        thread_id: str | None = None
        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                thread_id = data.get("message")
                break

    return thread_id

def delete_thread(*, user_id: str, thread_id: str) -> None:
    # prefer v5 for delete
    requests.delete(f"{FASTAPI_BASE_URL}/v5/threads/{thread_id}", headers=auth_headers(user_id=user_id), timeout=None)  # noqa: S113


# Abstract classes
#
class FastAPIUser(HttpUser):
    host = FASTAPI_BASE_URL
    abstract = True


class FlaskUser(HttpUser):
    host = FLASK_BASE_URL
    abstract = True


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
    thread_ids: list[str]
    user_id: str

    def on_start(self) -> None:
        self.user_id = str(uuid4())
        self.thread_ids = []
        for _ in range(NUM_THREADS_TO_CREATE):
            thread_id = create_thread(user_id=self.user_id)
            if thread_id:
                self.thread_ids.append(thread_id)

    def on_stop(self) -> None:
        for thread_id in self.thread_ids:
            delete_thread(user_id=self.user_id, thread_id=thread_id)

    @task
    def get_threads(self) -> None:
        self.client.get("/v5/threads/", headers=auth_headers(user_id=self.user_id))


class FlaskGetThreadListUser(FlaskUser):
    thread_ids: list[str]
    user_id: str

    def on_start(self) -> None:
        self.user_id = str(uuid4())
        self.thread_ids = []
        for _ in range(NUM_THREADS_TO_CREATE):
            thread_id = create_thread(user_id=self.user_id)
            if thread_id:
                self.thread_ids.append(thread_id)

    def on_stop(self) -> None:
        for thread_id in self.thread_ids:
            delete_thread(user_id=self.user_id, thread_id=thread_id)

    @task
    def get_threads(self) -> None:
        self.client.get("/v4/threads/", headers=auth_headers(user_id=self.user_id))


class FastAPICreateThreadUser(FastAPIUser):
    thread_ids: list[str]
    user_id: str

    def on_start(self) -> None:
        self.user_id = str(uuid4())
        self.thread_ids = []

    @task
    def create_thread(self) -> None:
        start = time.perf_counter()
        with self.client.post(
            "/v5/threads/chat",
            data={"model": MODEL, "content": "hello", "bypass_safety_check": "true"},
            headers=auth_headers(user_id=self.user_id),
            stream=True,
            catch_response=True,
        ) as resp:
            thread_id: str | None = None
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    if thread_id is None:
                        self.environment.events.request.fire(
                            request_type="POST",
                            name="/v5/threads/chat (TTFB)",
                            response_time=(time.perf_counter() - start) * 1000,
                            response_length=0,
                            exception=None,
                            context={},
                        )
                        thread_id = data.get("message")
            resp.success()  # type: ignore[union-attr]

        if thread_id:
            self.thread_ids.append(thread_id)

    def on_stop(self) -> None:
        for thread_id in self.thread_ids:
            delete_thread(user_id=self.user_id, thread_id=thread_id)

class FlaskCreateThreadUser(FlaskUser):
    thread_ids: list[str]
    user_id: str

    def on_start(self) -> None:
        self.user_id = str(uuid4())
        self.thread_ids = []

    @task
    def create_thread(self) -> None:
        start = time.perf_counter()
        with self.client.post(
            "/v4/threads/",
            json={"model": MODEL, "content": "hello", "bypass_safety_check": True},
            headers=auth_headers(user_id=self.user_id),
            stream=True,
            catch_response=True,
        ) as resp:
            thread_id: str | None = None
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    if thread_id is None:
                        self.environment.events.request.fire(
                            request_type="POST",
                            name="/v4/threads/ (TTFB)",
                            response_time=(time.perf_counter() - start) * 1000,
                            response_length=0,
                            exception=None,
                            context={},
                        )
                        thread_id = data.get("message")
            resp.success()  # type: ignore[union-attr]

        if thread_id:
            self.thread_ids.append(thread_id)

    def on_stop(self) -> None:
        for thread_id in self.thread_ids:
            delete_thread(user_id=self.user_id, thread_id=thread_id)
