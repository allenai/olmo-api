from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models import Model
from src.dao.engine_models.model_config import ModelHost, ModelConfig


from src.config.get_config import get_config


def get_cirrascale_model(model_config: ModelConfig) -> Model:
    cfg = get_config()
    port = model_config.model_id_on_host
    model_name = model_config.id.replace("cs-", "")

    return OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(
            base_url=f"{cfg.cirrascale_backend.base_url}:{port}/v1",
            api_key=cfg.cirrascale_backend.api_key,
        ),
    )
