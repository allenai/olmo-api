from pydantic import ByteSize, RootModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectin_polymorphic, sessionmaker

from src.config.Model import Model, MultiModalModel
from src.config.ModelConfig import FileRequiredToPromptOption
from src.dao.engine_models.model_config import ModelConfig as DAOModelConfig
from src.dao.engine_models.model_config import (
    MultiModalModelConfig as DAOMultiModalModelConfig,
)
from src.model_config.response_model import ResponseModel


class RootModelResponse(RootModel):
    root: list[Model | MultiModalModel] | list[ResponseModel]


def get_model_configs(
    session_maker: sessionmaker[Session], *, include_internal_models: bool = False
) -> RootModelResponse:
    with session_maker.begin() as session:
        polymorphic_loader_opt = selectin_polymorphic(DAOModelConfig, [DAOModelConfig, DAOMultiModalModelConfig])

        stmt = select(DAOModelConfig).options(polymorphic_loader_opt).order_by(DAOModelConfig.order.asc())

        if not include_internal_models:
            stmt = stmt.filter_by(internal=False)

        results = session.scalars(stmt).all()

        processed_results = []
        for m in results:
            item = Model(
                id=m.id,
                name=m.name,
                host=m.host,
                description=m.description,
                compute_source_id=m.model_id_on_host,
                model_type=m.model_type,
                system_prompt=m.default_system_prompt,
                family_id=m.family_id,
                family_name=m.family_name,
                available_time=m.available_time,
                deprecation_time=m.deprecation_time,
            )
            if isinstance(m, DAOMultiModalModelConfig):
                item = MultiModalModel(
                    id=m.id,
                    name=m.name,
                    host=m.host,
                    description=m.description,
                    compute_source_id=m.model_id_on_host,
                    model_type=m.model_type,
                    system_prompt=m.default_system_prompt,
                    family_id=m.family_id,
                    family_name=m.family_name,
                    available_time=m.available_time,
                    deprecation_time=m.deprecation_time,
                    accepted_file_types=m.accepted_file_types,
                    max_files_per_message=m.max_files_per_message,
                    require_file_to_prompt=m.require_file_to_prompt or FileRequiredToPromptOption.NoRequirement,
                    max_total_file_size=ByteSize(m.max_total_file_size) if m.max_total_file_size is not None else None,
                    allow_files_in_followups=m.allow_files_in_followups or False,
                )

            processed_results.append(item)

        return RootModelResponse.model_validate(processed_results)


def get_model_configs_admin(session_maker: sessionmaker[Session]) -> RootModelResponse:
    with session_maker.begin() as session:
        polymorphic_loader_opt = selectin_polymorphic(DAOModelConfig, [DAOModelConfig, DAOMultiModalModelConfig])

        stmt = select(DAOModelConfig).options(polymorphic_loader_opt).order_by(DAOModelConfig.order.asc())
        results = session.scalars(stmt).all()

        processed_results = [ResponseModel.model_validate(model) for model in results]

        return RootModelResponse.model_validate(processed_results)


def get_single_model_config_admin(
    session_maker: sessionmaker[Session], model_id: str
) -> DAOModelConfig | DAOMultiModalModelConfig | None:
    with session_maker.begin() as session:
        polymorphic_loader_opt = selectin_polymorphic(DAOModelConfig, [DAOModelConfig, DAOMultiModalModelConfig])
        stmt = select(DAOModelConfig).options(polymorphic_loader_opt).where(DAOModelConfig.id == model_id)

        return session.scalars(stmt).one_or_none()
