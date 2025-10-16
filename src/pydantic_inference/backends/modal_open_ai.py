from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.config.get_config import get_config
from src.dao.engine_models.model_config import ModelConfig

# Models hosted on vLLM always have this name
VLLM_MODEL_NAME = "llm"


def get_modal_openai_model(model_config: ModelConfig) -> Model:
    cfg = get_config()

    return OpenAIChatModel(
        model_name=VLLM_MODEL_NAME,
        provider=OpenAIProvider(
            # For Modal OpenAI APIs the "model_id" is the URL
            base_url=model_config.model_id_on_host,
            api_key=cfg.modal_openai.api_key.get_secret_value(),
        ),
    )
