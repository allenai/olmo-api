import os

from dotenv import load_dotenv
from locust import HttpUser, task, between
import logging


load_dotenv()


class PlaygroundAPITest(HttpUser):
    # wait_time = between(1, 2) # useful for setting a call

    @task
    def chat_with_image(self):
        # Format a request with an image or video to see how playground handles it

        token = os.getenv("USER_TOKEN")

        user_content = "hello world"

        headers = {"Authorization": f"Bearer {token}"}
        self.client.post(
            "/v4/threads/",
            headers=headers,
            files={
                "content": (None, user_content),
                "host": (None, "cirrascale_backend"),
                "model": (None, "cs-OLMo-2-0325-32B-Instruct"),
            },
        )
