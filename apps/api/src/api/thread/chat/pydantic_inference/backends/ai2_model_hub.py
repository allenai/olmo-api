from typing import TYPE_CHECKING

from pydantic_ai.providers.openai import OpenAIProvider

from api.config import settings
from core.pydantic_ai.open_ai_chat_model_video import OpenAIChatModelVideo
from db.models.model_config import ModelConfig

if TYPE_CHECKING:
    from pydantic_ai.models import Model


def get_ai2_model_hub_model(model_config: ModelConfig) -> Model:
    return OpenAIChatModelVideo(
        model_name=model_config.model_id_on_host,
        provider=OpenAIProvider(
            base_url=f"{settings.AI2_MODEL_HUB_BASE_URL}",
            api_key=settings.AI2_MODEL_HUB_API_KEY.get_secret_value(),
        ),
    )
