from pydantic import Field

from core.api_interface import APIInterface


class AuthenticatedClient(APIInterface):
    id: str | None = None
    client: str
    has_accepted_terms_and_conditions: bool = Field(title='Has Accepted Terms and Conditions')
    has_accepted_data_collection: bool = Field(title='Has Accepted Data Collection')
    has_accepted_media_collection: bool = Field(title='Has Accepted Media Collection')
    permissions: list[str] = Field(default_factory=list)
