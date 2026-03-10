from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request


@dataclass(kw_only=True)
class RequestClient:
    ip_address: str | None
    user_agent: str | None


def get_request_client_info(request: Request) -> RequestClient:
    return RequestClient(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


RequestClientDependency = Annotated[RequestClient, Depends(get_request_client_info)]
