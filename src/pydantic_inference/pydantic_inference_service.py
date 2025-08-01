from src.inference.ModalEngine import ModalEngine
from src.dao.engine_models.model_config import ModelHost, ModelConfig
from pydantic_ai.models import Model

from src.pydantic_inference.CirrascaleBackendEngine import get_cirrascale_model


def get_pydantic_inference_engine(model: ModelConfig) -> Model:
    match model.host:
        case ModelHost.CirrascaleBackend:
            return get_cirrascale_model(model)
        case _:
            raise ValueError(f"Unsupported model host: {model.host}")
