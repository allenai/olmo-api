from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Token:
    client: str
    created: datetime
    expires: datetime
    creator: Optional[str] = None

    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires
