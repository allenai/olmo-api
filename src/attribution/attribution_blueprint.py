from flask import Blueprint, Response, jsonify
from flask_pydantic_api.api_wrapper import pydantic_api
from werkzeug import exceptions

from src.attribution.attribution_service import GetAttributionRequest, get_attribution
from src.config.get_config import cfg
from src.dao.flask_sqlalchemy_session import current_session
from src.model_config.get_model_config_service import get_single_model_config_admin

from .infini_gram_api_client import Client

attribution_blueprint = Blueprint(name="attribution", import_name=__name__)


@attribution_blueprint.post(rule="")
@pydantic_api(name="Get CorpusLink spans and documents from a prompt", tags=["CorpusLink"])
def get_attribution_for_model_response(
    corpuslink_request: GetAttributionRequest,
) -> Response:
    infini_gram_client = Client(base_url=cfg.infini_gram.api_url, raise_on_unexpected_status=True)

    config = get_single_model_config_admin(current_session, corpuslink_request.model_id)
    if config is None:
        raise exceptions.NotFound

    attribution_response = get_attribution(
        request=corpuslink_request, infini_gram_client=infini_gram_client, model_config=config
    )

    return jsonify(attribution_response)
