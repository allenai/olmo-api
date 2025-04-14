from sqlalchemy import MetaData

from src.dao.base import Base

model_config_metadata = MetaData(schema="model_config")


class ModelConfigBase(Base):
    metadata = model_config_metadata
