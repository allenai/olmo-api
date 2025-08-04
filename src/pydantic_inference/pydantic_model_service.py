from pydantic_ai.models import Model

from src.dao.engine_models.model_config import ModelConfig, ModelHost

from .backends.cirrascale import get_cirrascale_model
from .backends.modal_open_ai import get_modal_openai_model
from .backends.pydantic_ai_test import get_test_model


def get_pydantic_model(model: ModelConfig) -> Model:
    match model.host:
        case ModelHost.CirrascaleBackend:
            return get_cirrascale_model(model)
        case ModelHost.ModalOpenAI:
            return get_modal_openai_model(model)
        case ModelHost.PydanticAiTest:
            return get_test_model()
        case _:
            raise ValueError(f"Unsupported model host: {model.host}")
