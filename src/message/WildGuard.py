import dataclasses
from typing import Optional

import modal

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
    modalClient: modal.Client

    def __init__(self) -> None:
        self.modalClient  = modal.Client.from_credentials(
            config.cfg.modal.token, config.cfg.modal.token_secret)


    def check_request(self, request: WildguardRequest) -> WildguardResponse:
        f = modal.Function.lookup("wildguard", "wildguard_api", client=self.modalClient)

        # the wildguard returns a generator that yields a single response
        result = list(f.remote_gen(request.prompt)).pop()

        return WildguardResponse(**result)
