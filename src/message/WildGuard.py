import dataclasses
import structlog
from time import time_ns

import modal

from src.config import get_config
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
)

logger = structlog.get_logger(__name__)


@dataclasses.dataclass
class WildguardRequest:
    prompt: str
    response: str | None = None


@dataclasses.dataclass
class WildguardResponse(SafetyCheckResponse):
    request_harmful: str | None = None
    response_refusal: str | None = None
    response_harmful: str | None = None

    def __init__(self, request_harmful, response_refusal, response_harmful):
        self.request_harmful = request_harmful
        self.response_harmful = response_harmful
        self.response_refusal = response_refusal

    def is_safe(self) -> bool:
        if self.request_harmful is None:
            msg = "WildGuard check result is None"
            raise RuntimeError(msg)

        return self.transform_value(self.request_harmful)

    def transform_value(self, val: str) -> bool:
        return val.lower() == "yes"


class WildGuard(SafetyChecker):
    client: modal.Client

    def __init__(self) -> None:
        self.client = modal.Client.from_credentials(get_config.cfg.modal.token, get_config.cfg.modal.token_secret)

    def check_request(self, req: SafetyCheckRequest) -> SafetyCheckResponse:
        f = modal.Function.lookup("wildguard", "wildguard_api", client=self.client)

        start_ns = time_ns()
        # the wildguard returns a generator that yields a single response
        result = list(f.remote_gen(req.content)).pop()
        end_ns = time_ns()

        response = WildguardResponse(
            request_harmful=result["request_harmful"],
            response_refusal=result["response_refusal"],
            response_harmful=result["response_harmful"],
        )

        logger.info(
            "wildguard_check",
            checker="WildGuard",
            prompt=req.content,
            duration_ms=(end_ns - start_ns) / 1_000_000,
            is_safe=response.is_safe(),
        )

        return response
