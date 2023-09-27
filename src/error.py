from flask import jsonify, request, render_template, make_response
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException
from werkzeug import http

def handle(e: HTTPException) -> ResponseReturnValue:
    accept = http.parse_accept_header(request.headers.get("Accept", "application/json"))
    match accept.best:
        case "text/html":
            r = make_response(render_template("error.jinja", title=f"HTTP {e.code}", message=e.description))
            r.status = e.code if e.code is not None else 500
            return r
        case _:
            code = e.code if e.code is not None else 500
            r = jsonify({ "error": { "code": code, "message": e.description }})
            r.status = code
            return r

