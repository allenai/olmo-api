from flask import jsonify, request, render_template, make_response
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException
from werkzeug import http
from typing import Optional
from logging import getLogger

def make_error_response(code: Optional[int] = None, message: Optional[str] = None) -> ResponseReturnValue:
    if code is None:
        code = 500
    if message is None:
        message = "Internal Server Error"
    accept = http.parse_accept_header(request.headers.get("Accept", "application/json"))
    match accept.best:
        case "text/html":
            return make_response(render_template("error.jinja", title=f"HTTP {code}", message=message), code)
        case _:
            return make_response(jsonify({ "error": { "code": code, "message": message }}), code)

def handle(e: Exception) -> ResponseReturnValue:
    getLogger(__name__).exception(e)
    if isinstance(e, HTTPException):
        return make_error_response(e.code, e.description)
    if isinstance(e, ValueError):
        return make_error_response(400, str(e))
    if isinstance(e, NotImplementedError):
        return make_error_response(400, str(e))
    return make_error_response(500, "Internal Server Error")

