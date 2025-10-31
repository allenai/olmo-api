"""
Logging Router (FastAPI) - V3
------------------------------

FastAPI router for client-side logging operations.
Converted from Flask blueprint in log/__init__.py.
"""

from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import Response

from src.log.log_service import LogEntry
from src.log.log_service import log as log_service

router = APIRouter(tags=["v3", "logging"])


@router.post("/", status_code=status.HTTP_204_NO_CONTENT)
async def log(
    log_data: dict = Body(...),
) -> Response:
    """Log a client-side event"""
    log_entry = LogEntry(
        severity=log_data.get("severity"),
        body=log_data.get("body"),
        resource=log_data.get("resource"),
        timestamp=log_data.get("timestamp"),
        attributes=log_data.get("attributes"),
    )

    if log_entry.is_valid is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more required fields were not provided"
        )

    log_service(log_entry)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
