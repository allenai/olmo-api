from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class Token:
    client: str
    is_anonymous_user: bool
    created: datetime | None = None
    expires: datetime | None = None
    creator: str | None = None

    def expired(self) -> bool:
        return self.expires is not None and datetime.now(UTC) >= self.expires
