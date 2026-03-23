from typing import TYPE_CHECKING

from db.models.model_config import ModelConfig, ModelHost

from .backends.ai2_model_hub import get_ai2_model_hub_model
from .backends.beaker_queues import get_beaker_queues_model
from .backends.cirrascale import get_cirrascale_model
from .backends.modal_open_ai import get_modal_openai_model
from .backends.pydantic_ai_test import get_test_model

if TYPE_CHECKING:
    from pydantic_ai.models import Model


def get_pydantic_model(model: ModelConfig) -> Model:
    match model.host:
        case ModelHost.Cirrascale:
            return get_cirrascale_model(model)
        case ModelHost.ModalOpenAI:
            return get_modal_openai_model(model)
        case ModelHost.BeakerQueues:
            return get_beaker_queues_model(model)
        case ModelHost.Ai2ModelHub:
            return get_ai2_model_hub_model(model)
        case ModelHost.TestBackend:
            return get_test_model()
        case _:
            unsupported_host_message = f"Unsupported model host: {model.host}"
            raise ValueError(unsupported_host_message)
