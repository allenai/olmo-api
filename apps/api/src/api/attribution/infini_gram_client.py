from typing import Annotated

from fastapi import Depends

from api.config import settings
from infini_gram_api_client import Client


def get_infini_gram_client():
    return InfiniGramClient()


class InfiniGramClient(Client):
    def __init__(self, *, base_url=settings.INFINI_GRAM_API_URL, raise_on_unexpected_status: bool = True):
        super().__init__(base_url=base_url, raise_on_unexpected_status=raise_on_unexpected_status)


InfiniGramClientDependency = Annotated[InfiniGramClient, Depends(get_infini_gram_client)]
