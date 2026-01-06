from pydantic_ai.models import Model
from pydantic_ai.providers.openai import OpenAIProvider

from db.models.model_config import ModelConfig
from src.config.get_config import get_config
from src.pydantic_inference.models.open_ai_chat_model_video import OpenAIChatModelVideo


def get_cirrascale_model(model_config: ModelConfig) -> Model:
    cfg = get_config()

    return OpenAIChatModelVideo(
        model_name=model_config.model_id_on_host,
        provider=OpenAIProvider(
            base_url=f"{cfg.cirrascale.base_url}",
            api_key=cfg.cirrascale.api_key.get_secret_value(),
        ),
    )
