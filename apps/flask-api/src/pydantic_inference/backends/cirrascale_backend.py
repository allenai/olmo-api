from pydantic_ai.models import Model
from pydantic_ai.providers.openai import OpenAIProvider

from db.models.model_config import ModelConfig
from src.config.get_config import get_config
from src.pydantic_inference.models.open_ai_chat_model_video import OpenAIChatModelVideo


def get_cirrascale_backend_model(model_config: ModelConfig) -> Model:
    cfg = get_config()
    port = model_config.model_id_on_host
    model_name = model_config.id.replace("cs-", "")

    return OpenAIChatModelVideo(
        model_name=model_name,
        provider=OpenAIProvider(
            base_url=f"{cfg.cirrascale_backend.base_url}:{port}/v1",
            api_key=cfg.cirrascale_backend.api_key,
        ),
    )
