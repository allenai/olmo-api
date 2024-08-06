from flask import Blueprint, Response, jsonify, request
from werkzeug import exceptions

from src.attribution.attribution_service import get_attribution
from src.config import cfg

from .infini_gram_api_client import Client

attribution_blueprint = Blueprint(name="attribution", import_name=__name__)


@attribution_blueprint.post(rule="")
def get_attribution_for_model_response() -> Response:
    if request.content_type != "application/json":
        raise exceptions.UnsupportedMediaType

    if request.json is None:
        raise exceptions.BadRequest("missing JSON body")

    infini_gram_client = Client(base_url=cfg.infini_gram.api_url)

    attribution_response = get_attribution(
        infini_gram_client=infini_gram_client,
    )

    return jsonify(attribution_response)
