from src.api_interface import APIInterface


class AuthenticatedClient(APIInterface):
    id: str | None = None
    client: str
    has_accepted_terms_and_conditions: bool
