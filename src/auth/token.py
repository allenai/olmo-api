from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Token:
    client: str
    is_anonymous_user: bool
    created: Optional[datetime] = None
    expires: Optional[datetime] = None
    creator: Optional[str] = None

    def expired(self) -> bool:
        return self.expires is not None and datetime.now(timezone.utc) >= self.expires
