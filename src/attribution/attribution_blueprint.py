from flask import Blueprint, Response, jsonify
from flask_pydantic_api.api_wrapper import pydantic_api

from src.attribution.attribution_service import GetAttributionRequest, get_attribution
from src.config import cfg

from .infini_gram_api_client import Client

attribution_blueprint = Blueprint(name="attribution", import_name=__name__)


@attribution_blueprint.post(rule="")
@pydantic_api(
    name="Get CorpusLink spans and documents from a prompt", tags=["CorpusLink"]
)
def get_attribution_for_model_response(
    corpuslink_request: GetAttributionRequest,
) -> Response:
    infini_gram_client = Client(
        base_url=cfg.infini_gram.api_url, raise_on_unexpected_status=True
    )

    attribution_response = get_attribution(
        request=corpuslink_request,
        infini_gram_client=infini_gram_client,
    )

    return jsonify(attribution_response)
