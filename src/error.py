from logging import getLogger
from typing import Optional

from flask import jsonify, make_response, render_template, request
from flask.typing import ResponseReturnValue
from pydantic import ValidationError
from werkzeug import http
from werkzeug.exceptions import HTTPException


def make_error_response(
    code: Optional[int] = None, message: Optional[str | dict] = None
) -> ResponseReturnValue:
    if code is None:
        code = 500
    if message is None:
        message = "Internal Server Error"
    accept = http.parse_accept_header(request.headers.get("Accept", "application/json"))
    match accept.best:
        case "text/html":
            return make_response(
                render_template("error.jinja", title=f"HTTP {code}", message=message),
                code,
            )
        case _:
            if isinstance(message, str):
                return make_response(
                    jsonify({"error": {"code": code, "message": message}}), code
                )
            else:
                return make_response(jsonify({"error": {"code": code, **message}}))


def handle(e: Exception) -> ResponseReturnValue:
    getLogger(__name__).exception(e)
    if isinstance(e, HTTPException):
        return make_error_response(e.code, e.description)
    if isinstance(e, ValidationError):
        return make_error_response(
            400,
            {"message": str(e), "validation_errors": e.errors(include_context=False)},
        )
    if isinstance(e, ValueError):
        return make_error_response(400, str(e))
    if isinstance(e, NotImplementedError):
        return make_error_response(400, str(e))
    return make_error_response(500, "Internal Server Error")
