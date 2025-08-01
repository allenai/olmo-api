from pydantic_ai.models import Model

from src.dao.engine_models.model_config import ModelConfig, ModelHost
from src.pydantic_inference.backends.cirrascale import get_cirrascale_model
from src.pydantic_inference.backends.modal_open_ai import get_modal_openai_model



def get_pydantic_inference_engine(model: ModelConfig) -> Model:
    match model.host:
        case ModelHost.CirrascaleBackend:
            return get_cirrascale_model(model)
        case ModelHost.ModalOpenAI:
            return get_modal_openai_model(model)
        case _:
            raise ValueError(f"Unsupported model host: {model.host}")
