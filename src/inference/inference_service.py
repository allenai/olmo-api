from collections.abc import Sequence

from src.config import get_config
from src.config.Model import Model, MultiModalModel
from src.dao.engine_models.model_config import ModelHost
from src.inference.BeakerQueuesEngine import BeakerQueuesEngine
from src.inference.InferDEngine import InferDEngine
from src.inference.InferenceEngine import InferenceEngine
from src.inference.ModalEngine import ModalEngine


def get_available_models() -> Sequence[Model | MultiModalModel]:
    return get_config.cfg.models


def get_engine(host: ModelHost) -> InferenceEngine:
    match host:
        case ModelHost.InferD:
            return InferDEngine()
        case ModelHost.BeakerQueues:
            return BeakerQueuesEngine()
        case ModelHost.Modal | _:
            return ModalEngine()
