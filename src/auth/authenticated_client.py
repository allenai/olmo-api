from typing import Optional

from src.api_interface import APIInterface


class AuthenticatedClient(APIInterface):
    id: Optional[str] = None
    client: str
    has_accepted_terms_and_conditions: bool
