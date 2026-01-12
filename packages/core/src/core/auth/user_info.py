from dataclasses import dataclass


@dataclass
class UserInfo:
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
