from collections.abc import Sequence

from src.config import get_config
from src.config.Model import Model, MultiModalModel
from src.constants import OLMO_ASR_MODEL_ID
from src.dao.engine_models.model_config import ModelHost, ModelConfig
from src.inference.BeakerQueuesEngine import BeakerQueuesEngine
from src.inference.CirrascaleBackendEngine import CirrascaleBackendEngine
from src.inference.InferDEngine import InferDEngine
from src.inference.InferenceEngine import InferenceEngine
from src.inference.ModalEngine import ModalEngine
from src.inference.olmo_asr_engine import OlmoAsrModalEngine


def get_available_models() -> Sequence[Model | MultiModalModel]:
    return get_config.cfg.models


def get_engine(model: ModelConfig) -> InferenceEngine:
    match model.host:
        case ModelHost.InferD:
            return InferDEngine()
        case ModelHost.BeakerQueues:
            return BeakerQueuesEngine()
        case ModelHost.CirrascaleBackend:
            return CirrascaleBackendEngine(model.name, port=model.model_id_on_host)
        case ModelHost.Modal | _:
            if model == OLMO_ASR_MODEL_ID:
                # HACK: The OLMoASR model has some special handling. We'll want to correct that in the future
                return OlmoAsrModalEngine()
            return ModalEngine()
