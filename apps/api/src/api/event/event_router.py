from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

event_router = APIRouter()

logger = structlog.getLogger()


class Event(BaseModel):
    occurred: datetime
    type: str
    details: dict[str, Any]


# Log events from the UI
# Using post with path instead of a route prefix to prevent unnecessary redirects
@event_router.post("/event")
def event(event: Event) -> bool:
    logger.info("UI Event", type=event.type, event_date=event.occurred, details=event.details)
    return True
