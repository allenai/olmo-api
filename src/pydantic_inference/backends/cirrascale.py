from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.config.get_config import get_config
from src.dao.engine_models.model_config import ModelConfig


def get_cirrascale_model(model_config: ModelConfig) -> Model:
    cfg = get_config()

    return OpenAIChatModel(
        model_name=model_config.model_id_on_host,
        provider=OpenAIProvider(
            base_url=f"{cfg.cirrascale.base_url}",
            api_key=cfg.cirrascale.api_key.get_secret_value(),
        ),
    )
