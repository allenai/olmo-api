from sqlalchemy.orm import Session, sessionmaker

from src.dao.engine_models.model_config import ModelConfig


def delete_model_config(model_id: str, session_maker: sessionmaker[Session]):
    with session_maker.begin() as session:
        delete_model = session.query(ModelConfig).filter_by(id=model_id).first()
        if not delete_model:
            raise ValueError("Model config not found!")
        session.delete(delete_model)
