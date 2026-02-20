from sqlalchemy import select
from sqlalchemy.orm import selectin_polymorphic

from db.models.model_config import FilesOnlyModelConfig, ModelConfig, MultiModalModelConfig

polymorphic_loader_opt = selectin_polymorphic(ModelConfig, [ModelConfig, MultiModalModelConfig, FilesOnlyModelConfig])
base_model_config_select = select(ModelConfig).options(polymorphic_loader_opt)
