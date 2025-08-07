from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
import os

from src.config.get_config import get_config
from src.dao.engine_models.model_config import ModelConfig

# Models hosted on vLLM always have this name
VLLM_MODEL_NAME = "llm"


from dotenv import find_dotenv, load_dotenv


env_file = find_dotenv(".env")
load_dotenv(env_file)


def get_modal_openai_model(model_config: ModelConfig) -> Model:
    cfg = get_config()

    return OpenAIModel(
        model_name="gemini-2.5-flash-lite",  # TODO: REVERT BEFORE MERGE JUST USED FOR TESTING
        provider=OpenAIProvider(
            # For Modal OpenAI APIs the "model_id" is the URL
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=os.getenv("GEMINI_API_KEY") or "",
        ),
    )
