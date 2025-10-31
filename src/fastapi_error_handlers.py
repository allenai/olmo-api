"""
FastAPI Exception Handlers
---------------------------

Global exception handlers for FastAPI that match Flask's error handling behavior.
"""

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


async def validation_exception_handler(_request: Request, exc: RequestValidationError | ValidationError):
    """
    Handle Pydantic validation errors (both RequestValidationError and ValidationError).

    Returns a 400 Bad Request with validation error details in the same format
    as Flask's error handler.
    """
    logger.exception(exc)

    errors = exc.errors()

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": {"code": 400, "message": "Validation error", "validation_errors": errors}},
    )


async def value_error_handler(_request: Request, exc: ValueError):
    """
    Handle ValueError as 400 Bad Request.

    This matches Flask's behavior where ValueError is treated as a client error.
    """
    logger.exception(exc)
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": {"code": 400, "message": str(exc)}})


async def not_implemented_error_handler(_request: Request, exc: NotImplementedError):
    """
    Handle NotImplementedError as 400 Bad Request.

    This matches Flask's behavior.
    """
    logger.exception(exc)
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": {"code": 400, "message": str(exc)}})


async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle all other exceptions as 500 Internal Server Error.

    Supports content negotiation: returns HTML if Accept header includes text/html,
    otherwise returns JSON.
    """
    logger.exception(exc)

    # Check Accept header for content negotiation
    accept = request.headers.get("accept", "application/json")

    if "text/html" in accept:
        return HTMLResponse(
            content="<h1>HTTP 500</h1><p>Internal Server Error</p>",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": 500, "message": "Internal Server Error"}},
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.

    This should be called during app creation in the factory function.
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(NotImplementedError, not_implemented_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
