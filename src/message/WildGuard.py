import dataclasses
from typing import Optional

from inferd import Client as InferdClient

from src import config


@dataclasses.dataclass
class WildguardRequest:
    prompt: str
    response: Optional[str] = None


@dataclasses.dataclass
class WildguardResponse:
    request_harmful: Optional[bool] = None
    response_refusal: Optional[bool] = None
    response_harmful: Optional[bool] = None


class WildGuard:
    inferDClient: InferdClient
    computeSourceId: str

    def __init__(self) -> None:
        self.inferDClient = InferdClient(
            config.cfg.wildguard.address, config.cfg.wildguard.token
        )
        self.computeSourceId = config.cfg.wildguard.compute_source_id

    def check_request(self, request: WildguardRequest) -> WildguardResponse:
        payload = dataclasses.asdict(request)

        # the wildguard returns a generator that yields a single response
        result = list(self.inferDClient.infer(self.computeSourceId, payload)).pop()

        return WildguardResponse(
            request_harmful=self.transform_value(result["request_harmful"]),
            response_refusal=self.transform_value(result["response_refusal"]),
            response_harmful=self.transform_value(result["response_harmful"]),
        )

    def transform_value(self, val: str):
        if val == "yes":
            return True
        if val == "no":
            return False
        return None
