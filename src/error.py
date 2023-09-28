from flask import jsonify, request, render_template, make_response
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException
from werkzeug import http
from typing import Optional
from logging import getLogger

import elasticsearch8 as es8

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

def handle_http(e: HTTPException) -> ResponseReturnValue:
    getLogger(__name__).exception(e)
    return make_error_response(e.code, e.description)

def handle_es(e: es8.exceptions.ApiError) -> ResponseReturnValue:
    getLogger(__name__).exception(e)

    # Do our best to unpack a meaningful error.
    # TODO: manifest friendlier (and safer) errors via exhaustive pattern matching
    details = []
    causes = e.body.get("error", {}).get("root_cause", [])
    for cause in causes:
        reason = cause.get("reason")
        if reason is not None:
            details.append(reason)

    # e.message isn't useful for the client, but we'll include it right now, as we currently
    # opt for verbosity over user-friendliness
    message = f"{e.message}: {', '.join(details)}"
    return make_error_response(e.status_code, message)

