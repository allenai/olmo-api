from src.api_interface import APIInterface


class AuthenticatedClient(APIInterface):
    client: str
    has_accepted_terms_and_conditions: bool
