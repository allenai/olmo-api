
from src.api_interface import APIInterface

from sqlalchemy.orm import Session, sessionmaker
from src.dao.engine_models.model_config import ModelConfig

class DeleteModelConfigRequest(APIInterface):
    id: str

def delete_model_config(request: DeleteModelConfigRequest, session_maker: sessionmaker[Session]):
    with session_maker.begin() as session:
        delete_model = session.query(ModelConfig).filter_by(id=request.id).first()
        if not delete_model:
            raise ValueError("Model config not found!")
        session.delete(delete_model)
        session.flush()


