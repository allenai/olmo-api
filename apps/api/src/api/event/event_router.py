import logging
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

event_router = APIRouter()

logger = logging.getLogger()

class Event(BaseModel):
    occurred: datetime
    type: str
    details: dict

# Log events from the UI
@event_router.post("/event")
def event(event: Event) -> None:
    logger.info("[Event] %s %s %s", event.type, event.occurred, event.details)
