import dataclasses
from time import time_ns
from typing import Optional

from flask import current_app
import modal

from src import config
from src.message.SafetyChecker import (
    SafetyCheckRequest,
    SafetyCheckResponse,
    SafetyChecker,
)


@dataclasses.dataclass
class WildguardRequest:
    prompt: str
    response: Optional[str] = None


@dataclasses.dataclass
class WildguardResponse(SafetyCheckResponse):
    request_harmful: Optional[str] = None
    response_refusal: Optional[str] = None
    response_harmful: Optional[str] = None

    def __init__(self, request_harmful, response_refusal, response_harmful):
        self.request_harmful = request_harmful
        self.response_harmful = response_harmful
        self.response_refusal = response_refusal

    def is_safe(self) -> bool:
        if self.request_harmful is None:
            raise RuntimeError("WildGuard check result is None")

        return self.transform_value(self.request_harmful)

    def transform_value(self, val: str) -> bool:
        if val.lower() == "yes":
            return True

        return False


class WildGuard(SafetyChecker):
    client: modal.Client

    def __init__(self) -> None:
        self.client = modal.Client.from_credentials(
            config.cfg.modal.token, config.cfg.modal.token_secret
        )

    def check_request(self, req: SafetyCheckRequest) -> SafetyCheckResponse:
        f = modal.Function.lookup("wildguard", "wildguard_api", client=self.client)

        start_ns = time_ns()
        # the wildguard returns a generator that yields a single response
        result = list(f.remote_gen(req.text)).pop()
        end_ns = time_ns()

        response = WildguardResponse(
            request_harmful=result["request_harmful"],
            response_refusal=result["response_refusal"],
            response_harmful=result["response_harmful"],
        )

        current_app.logger.info(
            {
                "checker": "GoogleModerateText",
                "prompt": req.text,
                "duration_ms": (end_ns - start_ns) / 1_000_000,
                "is_safe": response.is_safe(),
            }
        )

        return response
