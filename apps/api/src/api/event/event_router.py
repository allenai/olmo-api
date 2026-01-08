import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

event_router = APIRouter()

logger = logging.getLogger()

class Event(BaseModel):
    occurred: datetime
    type: str
    details: dict[str, Any]

# Log events from the UI
# Using post with path instead of a route prefix to prevent unnecessary redirects
@event_router.post("/event")
def event(event: Event) -> None:
    logger.info("[Event] %s %s %s", event.type, event.occurred, event.details)
