
from src.api_interface import APIInterface

from sqlalchemy.orm import Session, sessionmaker
from src.dao.engine_models.model_config import ModelConfig


class ModelOrder(APIInterface):
    id: str
    order: int

class ReorderModelConfigRequest(APIInterface):
    ordered_models: list[ModelOrder]

def reorder_model_config(request: ReorderModelConfigRequest, session_maker: sessionmaker[Session]):
    with session_maker.begin() as session:
        for model_order in request.ordered_models:
            model = session.get(ModelConfig, model_order.id)

            if model is None: 
                raise ValueError(f"Model with id '{model_order.id}' not found")
            
            model.order = model_order.order

