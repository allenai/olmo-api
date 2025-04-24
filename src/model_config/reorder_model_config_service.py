
from src.api_interface import APIInterface

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import update
from src.dao.engine_models.model_config import ModelConfig


class ModelOrder(APIInterface):
    id: str
    order: int

class ReorderModelConfigRequest(APIInterface):
    ordered_models: list[ModelOrder]

def reorder_model_config(request: ReorderModelConfigRequest, session_maker: sessionmaker[Session]):
      with session_maker.begin() as session:
        requested_ids = [model.id for model in request.ordered_models]

        existing_ids = {
            row[0] for row in session.query(ModelConfig.id).filter(ModelConfig.id.in_(requested_ids))
        }

        missing_ids = set(requested_ids) - existing_ids
        if missing_ids:
            raise ValueError(f"Model(s) not found: {', '.join(missing_ids)}")

        session.execute(
            update(ModelConfig),
            [
                {"id": model.id, "order": model.order}
                for model in request.ordered_models
            ]
        )

