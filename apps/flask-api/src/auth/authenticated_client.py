from core.api_interface import APIInterface
from pydantic import Field


class AuthenticatedClient(APIInterface):
    id: str | None = None
    client: str
    has_accepted_terms_and_conditions: bool
    has_accepted_data_collection: bool
    has_accepted_media_collection: bool
    permissions: list[str] = Field(default_factory=lambda: [])
