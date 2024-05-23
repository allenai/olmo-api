from flask import Blueprint, Response, request
from werkzeug import exceptions

from src.log.log_service import LogEntry
from src.log.log_service import log as log_service

logging_blueprint = Blueprint(name="logging", import_name=__name__)


@logging_blueprint.route("/", methods=["POST"])
def log() -> Response:
    if request.content_type != "application/json":
        raise exceptions.UnsupportedMediaType

    if request.json is None:
        raise exceptions.BadRequest("missing JSON body")

    log_entry = LogEntry(
        severity=request.json.get("severity"),
        body=request.json.get("body"),
        resource=request.json.get("resource"),
        timestamp=request.json.get("timestamp"),
        attributes=request.json.get("attributes"),
    )

    if log_entry.is_valid is False:
        raise exceptions.BadRequest("one or more required fields were not provided")

    log_service(log_entry)

    return Response(status=204)
