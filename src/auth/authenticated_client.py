from dataclasses import dataclass


@dataclass
class AuthenticatedClient:
    client: str
    has_accepted_terms_and_conditions: bool
