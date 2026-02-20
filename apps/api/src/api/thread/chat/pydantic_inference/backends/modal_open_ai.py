from pydantic_ai.models import Model
from pydantic_ai.providers.openai import OpenAIProvider

from db.models.model_config import ModelConfig
from src.config.get_config import cfg
from src.pydantic_inference.models.open_ai_chat_model_video import OpenAIChatModelVideo

# Models hosted on vLLM always have this name
VLLM_MODEL_NAME = "llm"


def get_modal_openai_model(model_config: ModelConfig) -> Model:
    client = OpenAIChatModelVideo(
        model_name=VLLM_MODEL_NAME,
        provider=OpenAIProvider(
            # For Modal OpenAI APIs the "model_id" is the URL
            base_url=model_config.model_id_on_host,
            api_key=cfg.modal_openai.api_key.get_secret_value(),
        ),
    )

    return client
